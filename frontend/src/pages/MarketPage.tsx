import { useEffect, useRef, useState } from "react";
import StockSearch from "../components/StockSearch";
import { getHistory, getQuote, type HistoryResponse, type Quote } from "../services/market";

function money(value: number | null | undefined) {
  return value == null ? "—" : value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function signedMoney(value: number | null | undefined) {
  if (value == null) return "—";
  return `${value >= 0 ? "+" : "−