using System.Collections.Generic;
using System.Text.Json;

namespace RippleWin
{
    public static class ValidatorShell
    {
        public static (bool ok, string message) ValidateAssetRow(Dictionary<string, object?> row)
        {
            if (!row.TryGetValue("raw_text", out var v) || v is null || string.IsNullOrWhiteSpace(v.ToString()))
                return (false, "Missing raw_text");
            // add more rules later (strategy_json, etc.)
            return (true, "OK");
        }
    }
}
