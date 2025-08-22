using Microsoft.Data.Sqlite;

namespace RippleWin
{
    public static class Seed
    {
        public static void InsertBaselineTerms(SqliteConnection conn)
        {
            using var tx = conn.BeginTransaction();
            using var ins = conn.CreateCommand();
            ins.Transaction = tx;
            ins.CommandText = @"
INSERT INTO x_domain_dict (term, domain, science_definition, human_analogy, human_context_strategy, version)
VALUES
('impurity','chemistry','Unwanted substance in a system','Feeling of dirtiness','Change solvent/context','v1'),
('solvent wash','chemistry','Use solvent to remove impurities','Shower/clean environment','Fresh towel/new scent/sunlight','v1'),
('chelation','chemistry','Ligand binds ions to remove them','Support binds sticky thought','Supportive partner/therapist dialogue','v1'),
('buffer','chemistry','Resists pH change','Stabilizing self-talk/norms','Affirmations/ground rules','v1'),
('radical scavenger','chemistry','Quenches reactive radicals','Friend/humor stops loops','Trusted friend/humor','v1'),
('symbolic closure','obviology','Ritual removes residue','Closure after task','New clothes/clean sheets','v1');
";
            ins.ExecuteNonQuery();
            tx.Commit();
        }
    }
}
