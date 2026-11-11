import contextlib
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import evaluasi
import main


class EvaluasiTest(unittest.TestCase):
    def test_checksums_match_windows_and_unix_line_endings(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "contoh.csv"
            path.write_bytes(b'\xef\xbb\xbfid,biaya\n1,12\n')
            unix_hash = evaluasi.sha_file(path)
            path.write_bytes(b'\xef\xbb\xbfid,biaya\r\n1,12\r\n')
            self.assertEqual(evaluasi.sha_file(path), unix_hash)

    def test_dataset_is_unique_reproducible_and_labels_have_proofs(self):
        with TemporaryDirectory() as first, TemporaryDirectory() as second, contextlib.redirect_stdout(io.StringIO()):
            left = evaluasi.buat_dataset(Path(first) / "peta.jsonl", jumlah=2, negatif=2, seed=17)
            right = evaluasi.buat_dataset(Path(second) / "peta.jsonl", jumlah=2, negatif=2, seed=17)
            self.assertEqual(left, right)
            self.assertEqual(len(left), 12)
            self.assertEqual(len({row["sha256_peta"] for row in left}), 12)
            self.assertEqual(evaluasi.baca_dataset(Path(first) / "peta.jsonl"), left)
            for row in left:
                peta = main.PetaMisi.dari_baris(tuple(row["petak"]))
                result = main.cari_rencana_astar(peta, main.kondisi_awal(peta))
                self.assertEqual(result is not None, row["harapan_layak"])

    def test_invalid_and_duplicate_dataset_are_rejected(self):
        with TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            path = Path(directory) / "peta.jsonl"
            rows = evaluasi.buat_dataset(path, jumlah=1, negatif=0, seed=6)
            with self.assertRaises(ValueError):
                evaluasi.buat_dataset(path, jumlah=1)
            path.write_text(json.dumps(rows[0]) + "\n" + json.dumps(rows[0]) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplikat"):
                evaluasi.baca_dataset(path)

    def test_measures_original_solver_and_replays_mission(self):
        entry = evaluasi.entri_peta(main.PETA_CONTOH["6x6"], "6x6", "acak_tervalidasi", 0, 1)
        calls_with_profiler = []
        original = main.cari_rencana_astar

        def solver(peta, initial):
            calls_with_profiler.append(sys.getprofile())
            return original(peta, initial)

        with patch.object(main, "cari_rencana_astar", side_effect=solver) as mock:
            row, raw = evaluasi.evaluasi_satu(entry, ulang=3)
        self.assertEqual(mock.call_count, 4)  # satu warmup + tiga pencarian terukur
        self.assertTrue(all(item is None for item in calls_with_profiler))
        self.assertEqual(len(raw), 3)
        self.assertEqual(row["misi_selesai"], 1)
        self.assertEqual(row["sesuai_harapan"], 1)
        self.assertEqual(row["biaya_total"], row["jumlah_aksi"])
        self.assertEqual(row["gerak"] + row["isi"] + row["tangani"], row["jumlah_aksi"])

    def test_unsolvable_has_blank_cost_and_real_counter(self):
        peta = main.PETA_CONTOH["6x6"].dengan_rintangan((1, 2)).dengan_rintangan((2, 1))
        entry = evaluasi.entri_peta(peta, "6x6", "pos_terkurung", 0, 1)
        previous = sys.getprofile()
        row, raw = evaluasi.evaluasi_satu(entry, ulang=2)
        self.assertIs(sys.getprofile(), previous)
        self.assertEqual(row["state_diperiksa"], 1)
        self.assertEqual(row["misi_selesai"], 0)
        self.assertEqual(row["sesuai_harapan"], 1)
        self.assertIsNone(row["biaya_total"])
        self.assertEqual(len(raw), 2)

    def test_full_small_run_exports_consistent_counts_and_report(self):
        with TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            path = Path(directory) / "data" / "peta.jsonl"
            output = Path(directory) / "hasil"
            evaluasi.buat_dataset(path, jumlah=1, negatif=2, seed=9)
            rows = evaluasi.jalankan(path, output, ulang=2)
            self.assertEqual(len(rows), 9)
            metadata = json.loads((output / "metadata_run.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["jumlah_pencarian_terukur"], 18)
            self.assertEqual(sum(row["misi_selesai"] for row in rows), 3)
            self.assertEqual(sum(row["sesuai_harapan"] for row in rows), 9)
            self.assertEqual(sum(row["jumlah_peta"] for row in evaluasi.ringkas(rows)), 9)
            report = (output / "laporan.md").read_text(encoding="utf-8")
            self.assertIn("9 peta unik", report)
            self.assertIn("Tidak ada pelatihan", report)


if __name__ == "__main__":
    unittest.main()
