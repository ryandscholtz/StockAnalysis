export interface BuyListItem {
  ticker: string
  company_name?: string
  exchange?: string
  current_price?: number
  currency?: string
  fair_value?: number
  margin_of_safety_pct?: number
  recommendation?: string
  quantity: number
  added_at: string
}
