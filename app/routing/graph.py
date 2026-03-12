GRAPH: dict[str, list[str]] = {
    "Bengaluru": ["MG Road", "Richmond Town", "Domlur"],
    "MG Road": ["Bengaluru", "Brigade Road", "Ulsoor"],
    "Richmond Town": ["Bengaluru", "Langford Road", "Adugodi"],
    "Domlur": ["Bengaluru", "Indiranagar", "Ejipura"],
    "Brigade Road": ["MG Road", "Richmond Town", "Adugodi"],
    "Ulsoor": ["MG Road", "Indiranagar", "CMH Road"],
    "Langford Road": ["Richmond Town", "Adugodi", "Shantinagar"],
    "Adugodi": ["Richmond Town", "Brigade Road", "Koramangala"],
    "Indiranagar": ["Domlur", "Ulsoor", "CMH Road"],
    "Ejipura": ["Domlur", "Koramangala", "Madiwala"],
    "CMH Road": ["Ulsoor", "Indiranagar", "100 Feet Road"],
    "100 Feet Road": ["CMH Road"],
    "Madiwala": ["Ejipura", "Koramangala", "Silk Board"],
    "Shantinagar": ["Langford Road", "Richmond Town", "Adugodi"],
    "Koramangala": ["Adugodi", "Ejipura", "Madiwala"],
}

TRAFFIC_COST: dict[str, int] = {"low": 1, "moderate": 5, "high": 10}

