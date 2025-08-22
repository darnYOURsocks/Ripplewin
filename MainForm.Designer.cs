using System.Windows.Forms;

namespace RippleWin
{
    partial class MainForm
    {
        private TextBox txtInput = null!;
        private Button btnIngest = null!;
        private TextBox txtSearch = null!;
        private Button btnSearch = null!;
        private DataGridView grid = null!;
        private TabControl tabs = null!;
        private TextBox tabRaw = null!;
        private TextBox tabKeywords = null!;
        private TextBox tabMetaphors = null!;
        private TextBox tabStructure = null!;
        private TextBox tabStrategy = null!;
        private TextBox tabSummary = null!;
        private TextBox tabHumanized = null!;

        private void InitializeComponent()
        {
            txtInput = new TextBox { Multiline = true, ScrollBars = ScrollBars.Vertical };
            btnIngest = new Button { Text = "Ingest" };
            txtSearch = new TextBox();
            btnSearch = new Button { Text = "Search" };
            grid = new DataGridView { ReadOnly = true, SelectionMode = DataGridViewSelectionMode.FullRowSelect, AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill };
            tabs = new TabControl();
            tabRaw = CreateTabBox();
            tabKeywords = CreateTabBox();
            tabMetaphors = CreateTabBox();
            tabStructure = CreateTabBox();
            tabStrategy = CreateTabBox();
            tabSummary = CreateTabBox();
            tabHumanized = CreateTabBox();

            var pageRaw = new TabPage("Raw"); pageRaw.Controls.Add(tabRaw);
            var pageKw = new TabPage("Keywords"); pageKw.Controls.Add(tabKeywords);
            var pageMet = new TabPage("Metaphors"); pageMet.Controls.Add(tabMetaphors);
            var pageStruc = new TabPage("Structure"); pageStruc.Controls.Add(tabStructure);
            var pageStrat = new TabPage("Strategy"); pageStrat.Controls.Add(tabStrategy);
            var pageSum = new TabPage("Summary"); pageSum.Controls.Add(tabSummary);
            var pageHum = new TabPage("Humanized"); pageHum.Controls.Add(tabHumanized);
            tabs.Controls.AddRange(new Control[] { pageRaw, pageKw, pageMet, pageStruc, pageStrat, pageSum, pageHum });

            SuspendLayout();

            txtSearch.SetBounds(10, 10, 500, 30);
            btnSearch.SetBounds(520, 10, 100, 30);
            txtInput.SetBounds(10, 50, 610, 120);
            btnIngest.SetBounds(520, 180, 100, 30);
            grid.SetBounds(10, 220, 610, 180);
            tabs.SetBounds(630, 10, 540, 390);

            foreach (TabPage p in tabs.TabPages)
                if (p.Controls.Count > 0) p.Controls[0].Dock = DockStyle.Fill;

            Controls.AddRange(new Control[] { txtSearch, btnSearch, txtInput, btnIngest, grid, tabs });
            Text = "Ripple Win – Obviology Retrieval";
            ClientSize = new System.Drawing.Size(1185, 415);

            ResumeLayout(false);
        }

        private TextBox CreateTabBox()
            => new TextBox { Multiline = true, ReadOnly = true, ScrollBars = ScrollBars.Vertical, BorderStyle = BorderStyle.None };
    }
}
