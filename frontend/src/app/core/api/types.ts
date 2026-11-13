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
export type ReportLabel = Schemas['ReportLabel'];
export type ReportEntries = Schemas['ReportEntries'];
export type ReportEntry = Schemas['ReportEntry'];
export type ReportPeriod = Schemas['Period'];
export type ReportSeries = Schemas['ReportSeries'];
export type SeriesLabel = Schemas['SeriesLabel'];
export type SeriesPoint = Schemas['SeriesPoint'];

export type LimitRead = Schemas['LimitRead'];
export type LimitStatus = Schemas['LimitStatus'];
export type AlertRead = Schemas['AlertRead'];
export type AlertLevel = Schemas['AlertLevel'];
export type GoalRead = Schemas['GoalRead'];
export type GoalList = Schemas['GoalList'];
export type GoalCreate = Schemas['GoalCreate'];
export type GoalUpdate = Schemas['GoalUpdate'];
export type GoalType = Schemas['GoalType'];

export type AttachmentRead = Schemas['AttachmentRead'];
export type SignedUrl = Schemas['SignedUrl'];
export type ExportRead = Schemas['ExportRead'];
export type ReportExportCreate = Schemas['ReportExportCreate'];
export type TwoFactorSetup = Schemas['TwoFactorSetup'];
export type TwoFactorStatus = Schemas['TwoFactorStatus'];
export type RecoveryCodes = Schemas['RecoveryCodes'];
