using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace RippleWin
{
    public static class Propagation
    {
        public static string ToKeywordsJson(string raw)
        {
            var words = Regex.Matches(raw.ToLowerInvariant(), "[a-z][a-z0-9\-\.]{3,}")
                             .Select(m => m.Value)
                             .Distinct()
                             .Take(50)
                             .ToList();
            return JsonSerializer.Serialize(words);
        }

        public static string ToMetaphorsJson(string raw)
        {
            var pairs = new List<string[]>();
            string r = raw.ToLowerInvariant();
            void AddIf(string needle, string mapped)
            {
                if (r.Contains(needle)) pairs.Add(new[] { needle, mapped });
            }
            AddIf("dirty", "impurity");
            AddIf("washed", "solvent wash");
            AddIf("clean", "solvent wash");
            AddIf("loop", "radical scavenger");
            var obj = new Dictionary<string, object> { ["pairs"] = pairs };
            return JsonSerializer.Serialize(obj);
        }

        public static string ToStructureJson(string raw)
        {
            var sections = new List<string>();
            string r = raw.ToLowerInvariant();
            if (r.Contains("dirty") || r.Contains("washed") || r.Contains("clean"))
            {
                sections.Add("Impurity control");
                sections.Add("Chelation");
                sections.Add("Buffers");
            }
            if (r.Contains("loop")) sections.Add("Radical control");
            var obj = new Dictionary<string, object> { ["sections"] = sections.Distinct().ToList() };
            return JsonSerializer.Serialize(obj);
        }

        public static string ToStrategyJson(string raw)
        {
            var strategies = new List<Dictionary<string, object>>();
            void Push(string control, params string[] actions)
            {
                strategies.Add(new()
                {
                    ["chem_control"] = control,
                    ["actions"] = actions
                });
            }
            string r = raw.ToLowerInvariant();
            if (r.Contains("dirty") || r.Contains("washed") || r.Contains("clean"))
            {
                Push("solvent change", "fresh towel", "new scent", "sunlight");
                Push("chelation", "supportive partner/therapist dialogue");
                Push("buffer", "self-statement: 'I’m clean now'");
                Push("remove product", "symbolic closure: new clothes, clean sheets");
            }
            if (r.Contains("loop"))
            {
                Push("radical scavenger", "trusted friend/humor reassurance");
            }
            return JsonSerializer.Serialize(strategies);
        }

        public static string ToSummary(string raw)
        {
            return "User reports persistent feeling of dirtiness; mapped to precipitation/chelation analogies. " +
                   "Strategy: change solvent/context, add chelator/support, introduce buffer norms, " +
                   "scavenge radical loops, remove product via symbolic closure.";
        }

        public static (string framedTermsJson, string rawFilterJson, string humanizedSummaryText) ToExpansions(string raw)
        {
            var framed = new[]
            {
                new {
                    term = "dirty",
                    note = new { chem = "impurity", frame = "requires solvent/chelator" }
                }
            };
            var windows = new[]
            {
                new { term = "dirty", window = "I feel dirty all the time", position = 2 }
            };
            var human = "You feel persistently unclean even after washing. We can change context (fresh towel/new scent/sunlight), " +
                        "bind the sticky thought with support, and normalize with a stabilizing self-statement.";
            return (
                JsonSerializer.Serialize(framed),
                JsonSerializer.Serialize(windows),
                human
            );
        }
    }
}
