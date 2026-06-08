CATALOGO_TITOLI = [
    {
        "ticker": "AAPL",
        "nome": "Apple",
        "settore": "Technology",
        "mercato": "NASDAQ",
    },
    {
        "ticker": "MSFT",
        "nome": "Microsoft",
        "settore": "Technology",
        "mercato": "NASDAQ",
    },
    {
        "ticker": "NVDA",
        "nome": "NVIDIA",
        "settore": "Technology",
        "mercato": "NASDAQ",
    },
    {
        "ticker": "GOOGL",
        "nome": "Alphabet",
        "settore": "Technology",
        "mercato": "NASDAQ",
    },
    {
        "ticker": "ORCL",
        "nome": "Oracle",
        "settore": "Technology",
        "mercato": "NYSE",
    },
    {
        "ticker": "AMD",
        "nome": "Advanced Micro Devices",
        "settore": "Technology",
        "mercato": "NASDAQ",
    },
    {
        "ticker": "KO",
        "nome": "Coca-Cola",
        "settore": "Consumer Defensive",
        "mercato": "NYSE",
    },
    {
        "ticker": "PEP",
        "nome": "PepsiCo",
        "settore": "Consumer Defensive",
        "mercato": "NASDAQ",
    },
    {
        "ticker": "PG",
        "nome": "Procter & Gamble",
        "settore": "Consumer Defensive",
        "mercato": "NYSE",
    },
    {
        "ticker": "WMT",
        "nome": "Walmart",
        "settore": "Consumer Defensive",
        "mercato": "NYSE",
    },
    {
        "ticker": "JNJ",
        "nome": "Johnson & Johnson",
        "settore": "Healthcare",
        "mercato": "NYSE",
    },
    {
        "ticker": "PFE",
        "nome": "Pfizer",
        "settore": "Healthcare",
        "mercato": "NYSE",
    },
    {
        "ticker": "MRK",
        "nome": "Merck",
        "settore": "Healthcare",
        "mercato": "NYSE",
    },
    {
        "ticker": "JPM",
        "nome": "JPMorgan Chase",
        "settore": "Financial Services",
        "mercato": "NYSE",
    },
    {
        "ticker": "BAC",
        "nome": "Bank of America",
        "settore": "Financial Services",
        "mercato": "NYSE",
    },
    {
        "ticker": "GS",
        "nome": "Goldman Sachs",
        "settore": "Financial Services",
        "mercato": "NYSE",
    },
    {
        "ticker": "XOM",
        "nome": "Exxon Mobil",
        "settore": "Energy",
        "mercato": "NYSE",
    },
    {
        "ticker": "CVX",
        "nome": "Chevron",
        "settore": "Energy",
        "mercato": "NYSE",
    },
    {
        "ticker": "COP",
        "nome": "ConocoPhillips",
        "settore": "Energy",
        "mercato": "NYSE",
    },
]


def trova_titoli_simili_per_settore(
    settore: str,
    ticker_da_escludere: set[str],
    limite: int = 3,
) -> list[dict[str, str]]:
    """Restituisce alcuni titoli dello stesso settore."""

    settore_normalizzato = settore.strip().lower()

    return [
        titolo
        for titolo in CATALOGO_TITOLI
        if titolo["settore"].lower() == settore_normalizzato
        and titolo["ticker"] not in ticker_da_escludere
    ][:limite]
