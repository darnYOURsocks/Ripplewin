using Microsoft.Data.Sqlite;
using System;
using System.Linq;
using System.Text.Json;
using System.Windows.Forms;

namespace RippleWin
{
    public partial class MainForm : Form
    {
        private readonly SqliteConnection _conn;
        private readonly SearchService _svc;

        public MainForm()
        {
            InitializeComponent();
            _conn = Db.Open();
            _svc = new SearchService(_conn);

            btnIngest.Click += (_, __) => Ingest();
            btnSearch.Click += (_, __) => RunSearch();
            grid.CellDoubleClick += (_, e) => LoadRowFromGrid(e.RowIndex);

            RunSearch();
        }

        private void Ingest()
        {
            var raw = txtInput.Text.Trim();
            if (string.IsNullOrWhiteSpace(raw))
            {
                MessageBox.Show("Enter some text to ingest.");
                return;
            }
            var id = _svc.Ingest(raw);
            txtInput.Clear();
            RunSearch();
            LoadById(id);
        }

        private void RunSearch()
        {
            string q = txtSearch.Text.Trim();
            string? topic = null, metaphor = null; bool? hasStrategy = null;

            foreach (var token in q.Split(' ', StringSplitOptions.RemoveEmptyEntries))
            {
                if (token.StartsWith("topic:", StringComparison.OrdinalIgnoreCase)) topic = token[6..];
                else if (token.StartsWith("metaphor:", StringComparison.OrdinalIgnoreCase)) metaphor = token[9..];
                else if (token.Equals("hasStrategy:true", StringComparison.OrdinalIgnoreCase)) hasStrategy = true;
            }
            var free = string.Join(" ", q.Split(' ').Where(t => !(t.StartsWith("topic:") || t.StartsWith("metaphor:") || t.StartsWith("hasStrategy:"))));

            var rows = _svc.Search(string.IsNullOrWhiteSpace(free) ? null : free, topic, metaphor, hasStrategy);
            grid.DataSource = rows.Select(r => new
            {
                id = r["id"],
                raw = r["raw_text"],
                summary = r["summary_text"]
            }).ToList();
        }

        private void LoadRowFromGrid(int rowIndex)
        {
            if (rowIndex < 0 || rowIndex >= grid.Rows.Count) return;
            var idObj = grid.Rows[rowIndex].Cells["id"].Value;
            if (idObj is long id) LoadById(id);
        }

        private void LoadById(long id)
        {
            var d = _svc.GetById(id);
            if (d.Count == 0) return;

            tabRaw.Text = d["raw_text"]?.ToString() ?? "";
            tabKeywords.Text = PrettyJson(d["keywords_json"]?.ToString());
            tabMetaphors.Text = PrettyJson(d["metaphors_json"]?.ToString());
            tabStructure.Text = PrettyJson(d["structure_json"]?.ToString());
            tabStrategy.Text = PrettyJson(d["strategy_json"]?.ToString());
            tabSummary.Text = d["summary_text"]?.ToString() ?? "";

            using var cmd = _conn.CreateCommand();
            cmd.CommandText = "SELECT humanized_summary_text FROM expansions WHERE asset_id=$id ORDER BY id DESC LIMIT 1;";
            cmd.Parameters.AddWithValue("$id", id);
            var hum = cmd.ExecuteScalar() as string;
            tabHumanized.Text = hum ?? "";
        }

        private static string PrettyJson(string? raw)
        {
            if (string.IsNullOrWhiteSpace(raw)) return "";
            try
            {
                var doc = JsonDocument.Parse(raw);
                return JsonSerializer.Serialize(doc.RootElement, new JsonSerializerOptions { WriteIndented = true });
            }
            catch { return raw!; }
        }
    }
}
