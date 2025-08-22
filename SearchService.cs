using Microsoft.Data.Sqlite;
using System.Collections.Generic;
using System.Text.Json;

namespace RippleWin
{
    public class SearchService
    {
        private readonly SqliteConnection _conn;
        public SearchService(SqliteConnection conn) => _conn = conn;

        public long Ingest(string rawText)
        {
            var keywords = Propagation.ToKeywordsJson(rawText);
            var metaphors = Propagation.ToMetaphorsJson(rawText);
            var structure = Propagation.ToStructureJson(rawText);
            var strategy = Propagation.ToStrategyJson(rawText);
            var summary = Propagation.ToSummary(rawText);
            var (framed, windows, human) = Propagation.ToExpansions(rawText);

            using var tx = _conn.BeginTransaction();

            using var ins = _conn.CreateCommand();
            ins.Transaction = tx;
            ins.CommandText = @"
INSERT INTO assets (type, source, created_at, raw_text, keywords_json, metaphors_json, structure_json, strategy_json, summary_text)
VALUES ('conversation', NULL, strftime('%s','now'), $raw, $kw, $met, $struc, $strat, $sum);
SELECT last_insert_rowid();";
            ins.Parameters.AddWithValue("$raw", rawText);
            ins.Parameters.AddWithValue("$kw", keywords);
            ins.Parameters.AddWithValue("$met", metaphors);
            ins.Parameters.AddWithValue("$struc", structure);
            ins.Parameters.AddWithValue("$strat", strategy);
            ins.Parameters.AddWithValue("$sum", summary);
            var id = (long)ins.ExecuteScalar()!;

            using var ins2 = _conn.CreateCommand();
            ins2.Transaction = tx;
            ins2.CommandText = @"
INSERT INTO expansions (asset_id, framed_terms_json, raw_filter_json, humanized_summary_text, created_at)
VALUES ($aid, $framed, $rawf, $human, strftime('%s','now'));";
            ins2.Parameters.AddWithValue("$aid", id);
            ins2.Parameters.AddWithValue("$framed", framed);
            ins2.Parameters.AddWithValue("$rawf", windows);
            ins2.Parameters.AddWithValue("$human", human);
            ins2.ExecuteNonQuery();

            tx.Commit();
            return id;
        }

        public List<Dictionary<string, object?>> Search(string? q = null, string? topic = null, string? metaphor = null, bool? hasStrategy = null)
        {
            var sql = @"
SELECT id, type, source, created_at, raw_text, summary_text, keywords_json, metaphors_json, structure_json, strategy_json
FROM assets
WHERE 1=1";
            var ps = new List<(string, object?)>();

            if (!string.IsNullOrWhiteSpace(q))
            {
                sql += " AND raw_text LIKE $q";
                ps.Add(("$q", $"%{q}%"));
            }
            if (!string.IsNullOrWhiteSpace(topic))
            {
                sql += " AND EXISTS (SELECT 1 FROM json_each(structure_json, '$.sections') WHERE value LIKE $topic)";
                ps.Add(("$topic", $"%{topic}%"));
            }
            if (!string.IsNullOrWhiteSpace(metaphor))
            {
                sql += " AND EXISTS (SELECT 1 FROM json_each(metaphors_json, '$.pairs') " +
                       "WHERE json_array_length(value)=2 AND (json_extract(value,'$[0]') LIKE $m OR json_extract(value,'$[1]') LIKE $m))";
                ps.Add(("$m", $"%{metaphor}%"));
            }
            if (hasStrategy == true)
            {
                sql += " AND json_array_length(strategy_json, '$') > 0";
            }

            using var cmd = _conn.CreateCommand();
            cmd.CommandText = sql;
            foreach (var (k, v) in ps) cmd.Parameters.AddWithValue(k, v);

            var rows = new List<Dictionary<string, object?>>();
            using var reader = cmd.ExecuteReader();
            while (reader.Read())
            {
                var d = new Dictionary<string, object?>
                {
                    ["id"] = reader.GetInt64(0),
                    ["raw_text"] = reader.GetString(4),
                    ["summary_text"] = reader.IsDBNull(5) ? null : reader.GetString(5),
                    ["keywords_json"] = reader.IsDBNull(6) ? null : reader.GetString(6),
                    ["metaphors_json"] = reader.IsDBNull(7) ? null : reader.GetString(7),
                    ["structure_json"] = reader.IsDBNull(8) ? null : reader.GetString(8),
                    ["strategy_json"] = reader.IsDBNull(9) ? null : reader.GetString(9)
                };
                rows.Add(d);
            }
            return rows;
        }

        public Dictionary<string, object?> GetById(long id)
        {
            using var cmd = _conn.CreateCommand();
            cmd.CommandText = "SELECT * FROM assets WHERE id=$id";
            cmd.Parameters.AddWithValue("$id", id);

            using var r = cmd.ExecuteReader();
            if (!r.Read()) return new();

            var cols = new Dictionary<string, object?>();
            for (int i = 0; i < r.FieldCount; i++)
                cols[r.GetName(i)] = r.IsDBNull(i) ? null : r.GetValue(i);
            return cols;
        }
    }
}
