import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/app/components/ui/tabs';
import type { SeasonInfo } from '@/app/lib/types';
import { Badge } from '@/app/components/ui/badge';

interface SeasonsTabsProps {
  seasons?: SeasonInfo[];
}

function SeasonsTabs({ seasons = [] }: SeasonsTabsProps) {
  if (!seasons.length) {
    return <p className="text-sm text-muted-foreground">No seasons available.</p>;
  }

  const initial = String(seasons[0]?.season_number ?? 1);

  return (
    <Tabs defaultValue={initial} className="w-full">
      <TabsList className="mb-4">
        {seasons.map((season) => (
          <TabsTrigger key={season.season_number} value={String(season.season_number)}>
            Season {season.season_number}
          </TabsTrigger>
        ))}
      </TabsList>
      {seasons.map((season) => (
        <TabsContent key={season.season_number} value={String(season.season_number)}>
          <div className="space-y-3">
            {season.episodes.map((episode) => (
              <div
                key={episode.episode_number}
                className="flex items-center justify-between rounded-2xl border border-border/60 bg-background/60 px-4 py-3 text-sm"
              >
                <div>
                  <p className="font-medium text-foreground">
                    {episode.episode_number}. {episode.title}
                  </p>
                </div>
                {episode.watched ? <Badge variant="success">Watched</Badge> : <Badge variant="outline">Unwatched</Badge>}
              </div>
            ))}
          </div>
        </TabsContent>
      ))}
    </Tabs>
  );
}

export default SeasonsTabs;
