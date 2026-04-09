export const STANCE_CATEGORIES = [
  'cosponsor',
  'publicly-supports',
  'leaning-support',
  'silent',
  'leaning-oppose',
  'publicly-opposes',
] as const;

export type StanceCategory = (typeof STANCE_CATEGORIES)[number];

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

export const PARTY_LABELS: Record<string, string> = {
  D: 'Democrat',
  R: 'Republican',
  I: 'Independent',
};
