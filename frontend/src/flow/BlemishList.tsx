import type { Label, Track } from "../protocol/types";
import { areaName, LABEL_INFO, ZONE_NAMES } from "../lib/blemishInfo";

export function BlemishList({ tracks, selected, onSelect, detailId }: {
  detailId: string; tracks: Track[]; selected: number | undefined; onSelect: (id: number) => void;
}) {
  const labels = [...new Set(tracks.map(track => track.label))] as Label[];
  return <section className="blemish-list" aria-label="All areas">
    <h2 className="sr-only">All areas</h2>
    {labels.map(label => {
      const group = tracks.filter(track => track.label === label);
      return <div key={label}><h3>{LABEL_INFO[label].plural} <span className="result-muted">({group.length})</span></h3>
        <ul>{group.map((track, index) => <li key={track.id}><button type="button" aria-pressed={track.id === selected}
          aria-label={areaName(track, index)} aria-controls={detailId}
          onClick={() => onSelect(track.id)}>{LABEL_INFO[label].name} {index + 1}<span>{ZONE_NAMES[track.zone]}</span></button></li>)}</ul>
      </div>;
    })}
  </section>;
}
