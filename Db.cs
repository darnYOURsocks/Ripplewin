using Microsoft.Data.Sqlite;
using System;
using System.IO;

namespace RippleWin
{
    public static class Db
    {
        public static readonly string DbPath = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "RippleWin", "ripple.db");

        public static SqliteConnection Open()
        {
            var dir = Path.GetDirectoryName(DbPath)!;
            if (!Directory.Exists(dir)) Directory.CreateDirectory(dir);

            var conn = new SqliteConnection($"Data Source={DbPath}");
            conn.Open();
            ApplySchema(conn);
            return conn;
        }

        private static void ApplySchema(SqliteConnection conn)
        {
            using var cmd = conn.CreateCommand();
            cmd.CommandText = @"
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS assets (
  id INTEGER PRIMARY KEY,
  type TEXT NOT NULL,
  source TEXT,
  created_at INTEGER NOT NULL,
  raw_text TEXT NOT NULL,
  keywords_json TEXT,
  metaphors_json TEXT,
  structure_json TEXT,
  strategy_json TEXT,
  summary_text TEXT
);

CREATE TABLE IF NOT EXISTS expansions (
  id INTEGER PRIMARY KEY,
  asset_id INTEGER NOT NULL,
  framed_terms_json TEXT,
  raw_filter_json TEXT,
  humanized_summary_text TEXT,
  created_at INTEGER NOT NULL,
  FOREIGN KEY(asset_id) REFERENCES assets(id)
);

CREATE TABLE IF NOT EXISTS x_domain_dict (
  id INTEGER PRIMARY KEY,
  term TEXT,
  domain TEXT,
  science_definition TEXT,
  human_analogy TEXT,
  human_context_strategy TEXT,
  version TEXT
);";
            cmd.ExecuteNonQuery();

            using var check = conn.CreateCommand();
            check.CommandText = "SELECT COUNT(*) FROM x_domain_dict;";
            var count = (long)check.ExecuteScalar()!;
            if (count == 0) Seed.InsertBaselineTerms(conn);
        }
    }
}
