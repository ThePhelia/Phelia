import { useMemo } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/app/components/ui/tabs';
import DetailHeader from '@/app/components/Detail/DetailHeader';
import TracksList from '@/app/components/Detail/TracksList';
import SeasonsTabs from '@/app/components/Detail/SeasonsTabs';
import RecommendationsRail from '@/app/components/Rails/RecommendationsRail';
import type { DetailResponse } from '@/app/lib/types';

interface DetailContentProps {
  detail: DetailResponse;
}

function DetailContent({ detail }: DetailContentProps) {
  const tabs = useMemo(() => {
    const base = ['overview', 'cast', 'related'];
    if (detail.seasons?.length) base.splice(2, 0, 'seasons');
    if (detail.tracks?.length) base.splice(2, 0, 'tracks');
    return base;
  }, [detail]);

  return (
    <div className="space-y-8">
      <DetailHeader detail={detail} />
      <Tabs defaultValue={tabs[0]} className="w-full">
        <TabsList className="flex flex-wrap gap-2">
          {tabs.map((tab) => (
            <TabsTrigger key={tab} value={tab} className="capitalize">
              {tab}
            </TabsTrigger>
          ))}
        </TabsList>
        <TabsContent value="overview" className="space-y-6">
          <section className="grid gap-4 md:grid-cols-[3fr_2fr]">
            <div>
              <h3 className="text-lg font-semibold text-foreground">Synopsis</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{detail.overview}</p>
            </div>
            <aside className="space-y-4 rounded-3xl border border-border/60 bg-background/50 p-4">
              <h4 className="text-sm font-semibold text-foreground">Availability</h4>
              <div className="space-y-3 text-sm text-muted-foreground">
                <div>
                  <p className="font-medium text-foreground">Streams</p>
                  <ul className="mt-1 space-y-1">
                    {detail.availability?.streams?.length ? (
                      detail.availability.streams.map((stream, index) => (
                        <li key={`${stream.provider}-${index}`}>
                          {stream.provider} • {stream.quality}
                        </li>
                      ))
                    ) : (
                      <li>No streams reported.</li>
                    )}
                  </ul>
                </div>
                <div>
                  <p className="font-medium text-foreground">Torrents</p>
                  <ul className="mt-1 space-y-1">
                    {detail.availability?.torrents?.length ? (
                      detail.availability.torrents.map((torrent, index) => (
                        <li key={`${torrent.provider}-${index}`}>
                          {torrent.provider} • {torrent.size} • {torrent.seeders} seeders
                        </li>
                      ))
                    ) : (
                      <li>No torrents available.</li>
                    )}
                  </ul>
                </div>
              </div>
            </aside>
          </section>
          {detail.links?.external?.length ? (
            <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
              {detail.links.external.map((link) => (
                <a
                  key={link.url}
                  href={link.url}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-full border border-border/60 px-3 py-1 hover:border-[color:var(--accent)] hover:text-foreground"
                >
                  {link.label}
                </a>
              ))}
            </div>
          ) : null}
        </TabsContent>
        <TabsContent value="cast">
          <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3">
            {detail.cast?.length ? (
              detail.cast.map((member) => (
                <div key={member.name} className="flex gap-3 rounded-2xl border border-border/60 bg-background/60 p-3">
                  <div className="h-14 w-14 overflow-hidden rounded-xl bg-foreground/10">
                    {member.photo ? (
                      <img src={member.photo} alt={member.name} className="h-full w-full object-cover" />
                    ) : null}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-foreground">{member.name}</p>
                    <p className="text-xs text-muted-foreground">{member.role}</p>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">No cast data.</p>
            )}
          </div>
        </TabsContent>
        {detail.tracks?.length ? (
          <TabsContent value="tracks">
            <TracksList tracks={detail.tracks} />
          </TabsContent>
        ) : null}
        {detail.seasons?.length ? (
          <TabsContent value="seasons">
            <SeasonsTabs seasons={detail.seasons} />
          </TabsContent>
        ) : null}
        <TabsContent value="related" className="space-y-6">
          <RecommendationsRail title="Similar" items={detail.similar} />
          <RecommendationsRail title="Recommended" items={detail.recommended} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default DetailContent;
