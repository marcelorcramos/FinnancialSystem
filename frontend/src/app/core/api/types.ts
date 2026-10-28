/**
 * Short names for the API types generated from the backend OpenAPI schema
 * (schema.ts, regenerate with `npm run api:types` while the API runs).
 */
import type { components } from './schema';

type Schemas = components['schemas'];

export type LabelKind = Schemas['LabelKind'];
export type LabelRead = Schemas['LabelRead'];
export type LabelCreate = Schemas['LabelCreate'];
export type LabelUpdate = Schemas['LabelUpdate'];
export type ColorSuggestions = Schemas['ColorSuggestions'];

export type MonthRead = Schemas['MonthRead'];
export type MonthCreate = Schemas['MonthCreate'];
export type MonthSummary = Schemas['MonthSummary'];
export type LabelSummary = Schemas['LabelSummary'];

export type IncomeRead = Schemas['IncomeRead'];
export type IncomeCreate = Schemas['IncomeCreate'];
export type IncomeUpdate = Schemas['IncomeUpdate'];

export type EntryRead = Schemas['EntryRead'];
export type EntryListItem = Schemas['EntryListItem'];
export type AllocationSet = Schemas['AllocationSet'];
export type AdditionCreate = Schemas['AdditionCreate'];
export type AdditionRead = Schemas['AdditionRead'];
export type TransferCreate = Schemas['TransferCreate'];
export type TransferRead = Schemas['TransferRead'];

export type ReportSummary = Schemas['ReportSummary'];
export type ReportPeriod = Schemas['Period'];
export type ReportSeries = Schemas['ReportSeries'];
export type SeriesLabel = Schemas['SeriesLabel'];
export type SeriesPoint = Schemas['SeriesPoint'];
