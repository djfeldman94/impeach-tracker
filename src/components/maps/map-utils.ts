import { geoAlbersUsa, geoPath, type GeoPermissibleObjects } from 'd3-geo';
import type { StanceCategory } from '../../styles/colors';

export const STANCE_COLORS: Record<StanceCategory, string> = {
  'cosponsor': '#1a7d34',
  'publicly-supports': '#34a853',
  'leaning-support': '#81c995',
  'silent': '#9e9e9e',
  'leaning-oppose': '#ef9a9a',
  'publicly-opposes': '#d32f2f',
};

export const STANCE_LABELS: Record<StanceCategory, string> = {
  'cosponsor': 'Co-sponsor',
  'publicly-supports': 'Publicly Supports',
  'leaning-support': 'Previously Voted For',
  'silent': 'Silent / Undeclared',
  'leaning-oppose': 'Previously Voted Against',
  'publicly-opposes': 'Publicly Opposes',
};

export interface MemberData {
  id: string;
  slug: string;
  fullName: string;
  party: 'D' | 'R' | 'I';
  state: string;
  district?: number;
  fipsCode: string;
  stance: StanceCategory;
  stanceSummary: string;
  phone?: string;
}

export function createProjection(width: number, height: number) {
  return geoAlbersUsa()
    .scale(width * 1.2)
    .translate([width / 2, height / 2]);
}

export function createPathGenerator(width: number, height: number) {
  const projection = createProjection(width, height);
  return geoPath(projection);
}

export function getStanceColor(stance: StanceCategory): string {
  return STANCE_COLORS[stance] || STANCE_COLORS['silent'];
}

export function getPartyLabel(party: string): string {
  const labels: Record<string, string> = { D: 'Democrat', R: 'Republican', I: 'Independent' };
  return labels[party] || party;
}

export function getPartyColor(party: string): string {
  const colors: Record<string, string> = {
    D: '#2166ac',
    R: '#b2182b',
    I: '#7b3294',
  };
  return colors[party] || '#666';
}

/**
 * Build a lookup map from FIPS code to member data.
 * For Senate, multiple members can share a FIPS (2 senators per state),
 * so we return an array.
 */
export function buildFipsLookup(members: MemberData[]): Map<string, MemberData[]> {
  const map = new Map<string, MemberData[]>();
  for (const m of members) {
    const existing = map.get(m.fipsCode) || [];
    existing.push(m);
    map.set(m.fipsCode, existing);
  }
  return map;
}
