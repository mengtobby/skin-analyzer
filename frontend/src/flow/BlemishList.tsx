import type { Label, Track } from "../protocol/types";
import { LABEL_INFO, ZONE_NAMES } from "../lib/blemishInfo";

export function BlemishList({ tracks, selected, onSelect }: {
  tracks: Track[]; selected: number | undefined; onSelect: (id: number) => void;
}) {
  const labels = [...new Set(tracks.map(track => track.label))] as Label[];
  return <section className="blemish-list" aria-label="All areas">
    {labels.map(label => {
      const group = tracks.filter(track => track.label === label);
      return <div key={label}><h3>{LABEL_INFO[label].plural} <span className="result-muted">({group.length})</span></h3>
        <ul>{group.map((track, index) => <li key={track.id}><button type="button" aria-pressed={track.id === selected}
          onClick={() => onSelect(track.id)}>{LABEL_INFO[label].name} {index + 1}<span>{ZONE_NAMES[track.zone]}</span></button></li>)}</ul>
      </div>;
    })}
  </section>;
}
