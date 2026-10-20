import type { Condition, Insight, Label, Report, Track, Zone } from "../protocol/types";

export const LABEL_INFO: Record<Label, { name: string; plural: string; description: string; condition: Condition }> = {
  papule: { name: "Papule", plural: "Papules", description: "A small raised bump that can look red or feel tender. It may appear when a pore becomes irritated.", condition: "inflammatory_acne" },
  pustule: { name: "Pustule", plural: "Pustules", description: "A raised spot with a pale centre and surrounding redness. Avoid picking to help limit irritation.", condition: "inflammatory_acne" },
  nodule: { name: "Nodule", plural: "Nodules", description: "A deeper-looking raised area that may feel tender. Persistent or painful bumps are worth discussing with a professional.", condition: "inflammatory_acne" },
  comedone: { name: "Comedone", plural: "Comedones", description: "A small clogged-looking pore, sometimes seen as a blackhead or whitehead. Oil and dead skin can collect at the pore opening.", condition: "comedonal_acne" },
  red_mark: { name: "Red mark", plural: "Red marks", description: "A flat pink or red-looking mark that can remain after a spot settles. Its appearance may soften over time.", condition: "post_inflammatory_erythema" },
  diffuse_redness: { name: "Diffuse redness", plural: "Areas of redness", description: "A broader area of visible redness rather than a single spot. Skin sensitivity and temporary irritation can affect its appearance.", condition: "diffuse_redness" },
  hyperpigmentation: { name: "Dark mark", plural: "Dark marks", description: "An area that looks darker than the surrounding skin. Sun exposure and marks left after irritation can contribute to uneven tone.", condition: "hyperpigmentation" },
  texture_irregularity: { name: "Uneven texture", plural: "Areas of uneven texture", description: "An area where the skin surface looks less smooth. Dryness and surface buildup can influence how texture appears.", condition: "uneven_texture" },
  fine_lines: { name: "Fine lines", plural: "Areas with fine lines", description: "Small visible lines on the skin surface. Dryness can make these lines look more noticeable.", condition: "dehydration_fine_lines" },
};

export const ZONE_NAMES: Record<Zone, string> = {
  forehead: "forehead", nose: "nose", left_cheek: "left cheek", right_cheek: "right cheek", chin: "chin", other: "other area",
};

export function insightFor(label: Label, report: Report): Insight | undefined {
  return report.insights.find(insight => insight.condition === LABEL_INFO[label].condition);
}

/** indexWithinLabel is zero-based within its type in capture order. */
export function areaName(track: Track, indexWithinLabel: number): string {
  return `${LABEL_INFO[track.label].name} ${indexWithinLabel + 1}, ${ZONE_NAMES[track.zone]}`;
}
