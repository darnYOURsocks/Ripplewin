using System;

namespace RippleWin
{
    public class Asset
    {
        public long Id { get; set; }
        public string Type { get; set; } = "conversation";
        public string? Source { get; set; }
        public long CreatedAt { get; set; } = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        public string RawText { get; set; } = "";

        public string? KeywordsJson { get; set; }
        public string? MetaphorsJson { get; set; }
        public string? StructureJson { get; set; }
        public string? StrategyJson { get; set; }
        public string? SummaryText { get; set; }
    }

    public class Expansion
    {
        public long Id { get; set; }
        public long AssetId { get; set; }
        public string? FramedTermsJson { get; set; }
        public string? RawFilterJson { get; set; }
        public string? HumanizedSummaryText { get; set; }
        public long CreatedAt { get; set; } = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
    }

    public class XDomainTerm
    {
        public long Id { get; set; }
        public string Term { get; set; } = "";
        public string Domain { get; set; } = "chemistry";
        public string ScienceDefinition { get; set; } = "";
        public string HumanAnalogy { get; set; } = "";
        public string HumanContextStrategy { get; set; } = "";
        public string Version { get; set; } = "v1";
    }
}
