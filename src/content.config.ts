import { defineCollection, z } from 'astro:content';
import { file } from 'astro/loaders';

const stanceEnum = z.enum([
  'cosponsor',
  'publicly-supports',
  'leaning-support',
  'silent',
  'leaning-oppose',
  'publicly-opposes',
]);

const sourceSchema = z.object({
  title: z.string(),
  url: z.string().url(),
  date: z.string(),
});

const districtOfficeSchema = z.object({
  city: z.string(),
  address: z.string(),
  phone: z.string(),
});

const memberSchema = z.object({
  id: z.string(),
  slug: z.string(),
  firstName: z.string(),
  lastName: z.string(),
  fullName: z.string(),
  party: z.enum(['D', 'R', 'I']),
  photoUrl: z.string().url().nullish(),
  state: z.string(),
  district: z.number().optional(),
  fipsCode: z.string(),

  stance: stanceEnum,
  stanceSummary: z.string(),
  stanceSources: z.array(sourceSchema).default([]),
  stanceUpdatedAt: z.string(),

  phone: z.string().nullish(),
  email: z.string().nullish(),
  website: z.string().url().nullish(),
  officeAddress: z.string().nullish(),
  districtOffices: z.array(districtOfficeSchema).default([]),

  twitter: z.string().nullish(),
  facebook: z.string().nullish(),

  termStart: z.string().nullish(),
  termEnd: z.string().nullish(),
  nextElection: z.string().nullish(),
});

const representatives = defineCollection({
  loader: file('src/content/representatives/members.json'),
  schema: memberSchema,
});

const senators = defineCollection({
  loader: file('src/content/senators/senators.json'),
  schema: memberSchema,
});

const governors = defineCollection({
  loader: file('src/content/governors/governors.json'),
  schema: memberSchema,
});

export const collections = { representatives, senators, governors };
