import json
import os

def ob(repo_newt, repo_modi="O", repo_eror="-", repo_etrm="-", repo_corr=None, repo_valu="-",
       bsb_newt=None, bsb_modi=None, bsb_eror=None, bsb_etrm=None, bsb_corr=None, bsb_valu=None,
       sl_newt=None, sl_modi=None, sl_eror=None, sl_etrm=None, sl_corr=None, sl_valu=None,
       ml_newt=None, ml_modi=None, ml_eror=None, ml_etrm=None, ml_corr=None, ml_valu=None):
    if repo_corr is None: repo_corr = repo_modi
    for attr in ['bsb_newt','bsb_modi','bsb_eror','bsb_etrm','bsb_corr','bsb_valu']:
        if locals()[attr] is None: locals()[attr] = locals()['repo_' + attr[4:]]
    for attr in ['sl_newt','sl_modi','sl_eror','sl_etrm','sl_corr','sl_valu']:
        if locals()[attr] is None: locals()[attr] = locals()['repo_' + attr[3:]]
    for attr in ['ml_newt','ml_modi','ml_eror','ml_etrm','ml_corr','ml_valu']:
        if locals()[attr] is None: locals()[attr] = locals()['repo_' + attr[3:]]
    bsb_newt = bsb_newt if bsb_newt is not None else repo_newt
    bsb_modi = bsb_modi if bsb_modi is not None else repo_modi
    bsb_eror = bsb_eror if bsb_eror is not None else repo_eror
    bsb_etrm = bsb_etrm if bsb_etrm is not None else repo_etrm
    bsb_corr = bsb_corr if bsb_corr is not None else repo_corr
    bsb_valu = bsb_valu if bsb_valu is not None else repo_valu
    sl_newt = sl_newt if sl_newt is not None else repo_newt
    sl_modi = sl_modi if sl_modi is not None else repo_modi
    sl_eror = sl_eror if sl_eror is not None else repo_eror
    sl_etrm = sl_etrm if sl_etrm is not None else repo_etrm
    sl_corr = sl_corr if sl_corr is not None else repo_corr
    sl_valu = sl_valu if sl_valu is not None else repo_valu
    ml_newt = ml_newt if ml_newt is not None else repo_newt
    ml_modi = ml_modi if ml_modi is not None else repo_modi
    ml_eror = ml_eror if ml_eror is not None else repo_eror
    ml_etrm = ml_etrm if ml_etrm is not None else repo_etrm
    ml_corr = ml_corr if ml_corr is not None else repo_corr
    ml_valu = ml_valu if ml_valu is not None else repo_valu
    return {
        "Repo": {"NEWT": repo_newt, "MODI": repo_modi, "EROR": repo_eror, "ETRM": repo_etrm, "CORR": repo_corr, "VALU": repo_valu},
        "BSB": {"NEWT": bsb_newt, "MODI": bsb_modi, "EROR": bsb_eror, "ETRM": bsb_etrm, "CORR": bsb_corr, "VALU": bsb_valu},
        "SL": {"NEWT": sl_newt, "MODI": sl_modi, "EROR": sl_eror, "ETRM": sl_etrm, "CORR": sl_corr, "VALU": sl_valu},
        "ML": {"NEWT": ml_newt, "MODI": ml_modi, "EROR": ml_eror, "ETRM": ml_etrm, "CORR": ml_corr, "VALU": ml_valu},
    }

fields = []

# TABLE 1: Counterparty Data (18 fields)
t1 = [
    (1, "Reporting timestamp", "Date and time of submission of the report to the TR", "ISO 8601 date-time", ob("M","M","M","M","M","M"), False, "Must be a valid UTC timestamp in ISO 8601 format"),
    (2, "Report submitting entity", "LEI of the entity submitting the report", "ISO 17442 LEI (20 chars)", ob("M","M","M","M","M","M"), False, "Must be a valid LEI format"),
    (3, "Reporting counterparty", "LEI of the reporting counterparty", "ISO 17442 LEI (20 chars)", ob("M","M","M","M","M","M"), False, "Must be a valid LEI"),
    (4, "Nature of the reporting counterparty", "Financial (F) or non-financial (N) counterparty", "F or N", ob("M","M","-","-","M","-"), False, "Must be F or N"),
    (5, "Sector of the reporting counterparty", "Nature of the reporting counterparty business activities", "Taxonomy codes (CDTI, INVF, ASSU)", ob("M","O","-","-","O","-"), False, "If field 4 is F, at least one value from FC taxonomy required"),
    (6, "Additional sector classification", "Additional NACE classification for NFC", "NACE Rev.2 code", ob("C","O","-","-","O","-"), False, "Required if field 4 is N"),
    (7, "Branch of the reporting counterparty", "Country of the branch through which the SFT is executed", "ISO 3166-1 alpha-2", ob("C","O","-","-","O","-"), False, "Must be a valid ISO country code"),
    (8, "Side of the counterparty", "Collateral provider or taker", "GIVE or TAKE", ob("M","M","-","-","M","-"), True, "Must be GIVE or TAKE. Mirror field: counterparties report opposite values"),
    (9, "Other counterparty", "LEI or client code of the other counterparty", "ISO 17442 LEI or client code", ob("M","M","M","M","M","M"), False, "Must be a valid LEI or client code"),
    (10, "Country of the other counterparty", "Country code of the other counterparty", "ISO 3166-1 alpha-2", ob("M","O","-","-","O","-"), False, "Must be a valid ISO country code"),
    (11, "Beneficiary", "LEI or client code of the beneficiary if different", "ISO 17442 LEI or client code", ob("C","O","-","-","O","-"), False, "Required if beneficiary differs from reporting counterparty"),
    (12, "Tri-party agent", "LEI of the tri-party agent", "ISO 17442 LEI", ob("C","O","-","-","O","-"), False, "Must be valid LEI if populated"),
    (13, "Broker", "LEI of the broker that intermediated the SFT", "ISO 17442 LEI", ob("O","O","-","-","O","-"), False, "Must be valid LEI if populated"),
    (14, "Clearing member", "LEI of the clearing member", "ISO 17442 LEI", ob("C","O","-","-","O","-"), False, "Required if SFT was cleared"),
    (15, "CSD participant or indirect participant", "LEI or BIC of the CSD participant", "ISO 17442 LEI or BIC", ob("C","O","-","-","O","-"), False, "Must be valid LEI or BIC if populated"),
    (16, "Agent lender", "LEI of the agent lender", "ISO 17442 LEI", ob("C","O","-","-","O","-",sl_newt="C",ml_newt="C"), False, "Required for securities lending where an agent acts on behalf"),
    (17, "UTI", "Unique Transaction Identifier", "UTI (max 52 chars)", ob("M","M","M","M","M","M"), False, "Must be unique, max 52 alphanumeric characters"),
    (18, "Report tracking number", "Unique number for internal tracking", "Max 52 chars", ob("M","M","M","M","M","M"), False, "Must be unique per report"),
]
for num, name, desc, fmt, obl, mirror, rule in t1:
    fields.append({"table":1,"number":num,"name":name,"description":desc,"format":fmt,"obligation":obl,"is_mirror":mirror,"validation_rule":rule})

# TABLE 2: Loan and Collateral Data (99 fields)
t2 = [
    (1, "Event date", "Date on which the reportable event took place", "ISO 8601 date", ob("M","M","M","M","M","M"), False, "Must be a valid date"),
    (2, "Type of SFT", "Type of securities financing transaction", "REPO, BSB, SL, ML", ob("M","-","-","-","-","-"), False, "Must be one of REPO, BSB, SL, ML"),
    (3, "Cleared", "Whether the SFT was centrally cleared", "Boolean", ob("M","O","-","-","O","-"), False, "Must be true or false"),
    (4, "Clearing timestamp", "Time and date when clearing took place", "ISO 8601 date-time", ob("C","O","-","-","O","-"), False, "Required if field 3 is true"),
    (5, "CCP", "LEI of the CCP that cleared the SFT", "ISO 17442 LEI", ob("C","O","-","-","O","-"), False, "Required if field 3 is true"),
    (6, "Trading venue", "MIC of the trading venue", "ISO 10383 MIC (4 chars)", ob("M","O","-","-","O","-"), False, "Must be valid MIC code or XXXX for OTC"),
    (7, "Master agreement type", "Reference to the master agreement", "Enumerated (GMRA, GMSLA, MSLA)", ob("M","O","-","-","O","-"), False, "Must be from allowed list"),
    (8, "Other master agreement type", "Name if Other is selected", "Free text (max 50 chars)", ob("C","O","-","-","O","-"), False, "Required if field 7 is Other"),
    (9, "Master agreement version", "Year of the master agreement version", "YYYY", ob("O","O","-","-","O","-"), False, "Must be a valid 4-digit year"),
    (10, "Execution timestamp", "Date and time of execution of the SFT", "ISO 8601 date-time", ob("M","O","-","-","O","-"), False, "Must be valid ISO 8601 datetime"),
    (11, "Value date (Start date)", "Settlement date of the opening leg", "ISO 8601 date", ob("M","O","-","-","O","-"), False, "Must be a valid date"),
    (12, "Maturity date (End date)", "Settlement date of the closing leg", "ISO 8601 date", ob("M","O","-","-","O","-"), False, "Must be a valid date or open for open-ended SFTs"),
    (13, "Termination date", "Actual termination date if different from maturity", "ISO 8601 date", ob("C","C","-","M","C","-"), False, "Must be a valid date"),
    (14, "Minimum notice period", "Min business days for notice before termination", "Integer", ob("C","O","-","-","O","-"), False, "Must be a positive integer if populated"),
    (15, "Earliest call-back date", "Earliest date lender can call back securities", "ISO 8601 date", ob("C","O","-","-","O","-"), False, "Must be a valid date"),
    (16, "General collateral indicator", "General or specific collateral", "GENE or SPEC", ob("C","O","-","-","O","-"), False, "Must be GENE or SPEC"),
    (17, "DBV indicator", "Delivery-by-value transaction", "Boolean", ob("C","O","-","-","O","-"), False, "Must be true or false"),
    (18, "Method used to provide collateral", "Title transfer or security interest", "TTCA or SICA or OTH", ob("M","O","-","-","O","-"), False, "Must be TTCA, SICA, or OTH"),
    (19, "Open term", "Whether SFT is open term (no fixed maturity)", "Boolean", ob("M","O","-","-","O","-"), False, "Must be true or false"),
    (20, "Termination optionality", "Termination optionality features", "EGRN, ETSB, NOAP", ob("C","O","-","-","O","-"), False, "Must be EGRN, ETSB, or NOAP"),
    (21, "Fixed rate", "Fixed rate of the repo or lending fee", "Decimal", ob("C","C","-","-","C","-"), False, "Must be numeric decimal"),
    (22, "Day count convention", "Day count convention for fixed rate", "Enumerated: A001-A020", ob("C","O","-","-","O","-"), False, "Must be valid day count convention code"),
    (23, "Floating rate", "Reference rate for floating rate", "Enumerated (EONA, SOFR, ESTR)", ob("C","C","-","-","C","-"), False, "Must be a valid benchmark rate identifier"),
    (24, "Floating rate reference period - time period", "Time period for floating rate reference", "YEAR, MNTH, WEEK, DAYS", ob("C","O","-","-","O","-"), False, "Must be valid time period code"),
    (25, "Floating rate reference period - multiplier", "Multiplier for the time period", "Integer", ob("C","O","-","-","O","-"), False, "Must be a positive integer"),
    (26, "Floating rate payment frequency - time period", "Payment frequency time period", "YEAR, MNTH, WEEK, DAYS", ob("C","O","-","-","O","-"), False, "Must be valid time period code"),
    (27, "Floating rate payment frequency - multiplier", "Multiplier for payment frequency", "Integer", ob("C","O","-","-","O","-"), False, "Must be a positive integer"),
    (28, "Floating rate reset frequency - time period", "Reset frequency time period", "YEAR, MNTH, WEEK, DAYS", ob("C","O","-","-","O","-"), False, "Must be valid time period code"),
    (29, "Floating rate reset frequency - multiplier", "Multiplier for reset frequency", "Integer", ob("C","O","-","-","O","-"), False, "Must be a positive integer"),
    (30, "Spread", "Spread over/under floating rate in basis points", "Decimal (basis points)", ob("C","O","-","-","O","-"), False, "Must be a numeric decimal"),
    (31, "Lending fee / Margin lending rate", "Fee or rate for securities/margin lending", "Decimal (percentage)", ob("C","C","-","-","C","-",sl_newt="M",ml_newt="M"), False, "Must be numeric decimal"),
    (32, "Exclusive arrangements", "Whether lending is on exclusive terms", "Boolean", ob("-","-","-","-","-","-",sl_newt="C",ml_newt="C"), False, "Must be true or false if populated"),
    (33, "Outstanding margin loan", "Total value of the outstanding margin loan", "Decimal amount", ob("-","-","-","-","-","-",ml_newt="M",ml_modi="M",ml_valu="M"), False, "Must be a positive numeric amount"),
    (34, "Base currency of outstanding margin loan", "Currency of the outstanding margin loan", "ISO 4217", ob("-","-","-","-","-","-",ml_newt="M",ml_modi="M",ml_valu="M"), False, "Must be a valid ISO 4217 currency code"),
    (35, "Short market value", "Market value of the short position", "Decimal amount", ob("-","-","-","-","-","-",ml_newt="C",ml_modi="C",ml_valu="C"), False, "Must be numeric if populated"),
    (36, "Principal amount on value date", "Cash value to be settled on value date", "Decimal amount", ob("M","O","-","-","O","-",sl_newt="-",ml_newt="-"), False, "Must be a positive numeric amount"),
    (37, "Principal amount on maturity date", "Cash value to be settled on maturity date", "Decimal amount", ob("M","O","-","-","O","-",sl_newt="-",ml_newt="-"), False, "Must be a positive numeric amount"),
    (38, "Principal amount currency", "Currency of the principal amount", "ISO 4217", ob("M","O","-","-","O","-",sl_newt="-",ml_newt="-"), False, "Must be valid ISO 4217 currency code"),
    (39, "Type of asset", "Type of security or commodity as collateral", "SECU, COMM, CASH", ob("M","O","-","-","O","-"), False, "Must be SECU, COMM, or CASH"),
    (40, "Security identifier", "ISIN of the security", "ISO 6166 ISIN (12 chars)", ob("C","O","-","-","O","-"), False, "Must be a valid ISIN if field 39 is SECU"),
    (41, "Classification of a security", "CFI code for the security", "ISO 10962 CFI (6 chars)", ob("C","O","-","-","O","-"), False, "Must be a valid 6-character CFI code"),
    (42, "Base product", "Base product for commodities", "Enumerated commodity codes", ob("C","O","-","-","O","-"), False, "Required if field 39 is COMM"),
    (43, "Sub product", "Sub product for commodities", "Enumerated commodity codes", ob("C","O","-","-","O","-"), False, "Required if field 42 is populated"),
    (44, "Further sub product", "Further sub product for commodities", "Enumerated commodity codes", ob("C","O","-","-","O","-"), False, "Required if field 43 is populated"),
    (45, "Quantity or nominal amount", "Quantity or nominal of security/commodity", "Decimal", ob("C","O","-","-","O","-"), False, "Must be a positive number"),
    (46, "Unit of measure", "Unit of measure for commodities", "Enumerated units", ob("C","O","-","-","O","-"), False, "Required if field 39 is COMM"),
    (47, "Currency of nominal amount", "Currency of the nominal amount", "ISO 4217", ob("C","O","-","-","O","-"), False, "Must be valid ISO 4217 code"),
    (48, "Security or commodity price", "Price per unit of security/commodity", "Decimal", ob("C","O","-","-","O","-"), False, "Must be a positive number"),
    (49, "Price currency", "Currency of the price", "ISO 4217", ob("C","O","-","-","O","-"), False, "Must be valid ISO 4217 code"),
    (50, "Security quality", "Credit quality classification", "INVG, NIVG, NOTR, NOAP", ob("C","O","-","-","O","-"), False, "Must be INVG, NIVG, NOTR or NOAP"),
    (51, "Maturity of the security", "Maturity date of the security", "ISO 8601 date", ob("C","O","-","-","O","-"), False, "Must be a valid date"),
    (52, "Issuer jurisdiction", "Jurisdiction of the issuer", "ISO 3166-1 alpha-2", ob("C","O","-","-","O","-"), False, "Must be a valid country code"),
    (53, "LEI of the issuer", "LEI of the issuer of the security", "ISO 17442 LEI", ob("C","O","-","-","O","-"), False, "Must be a valid LEI"),
    (54, "Collateral type", "Specific or general collateral", "SPEC or GENE", ob("C","O","-","-","O","-"), False, "Must be SPEC or GENE"),
    (55, "Availability for collateral reuse", "Whether collateral can be reused", "Boolean", ob("C","O","-","-","O","-"), False, "Must be true or false"),
    (56, "Collateral basket identifier", "ISIN of the collateral basket", "ISO 6166 ISIN", ob("C","O","-","-","O","-"), False, "Must be a valid ISIN if populated"),
    (57, "Portfolio code", "Unique code for portfolio-level reporting", "Max 52 chars", ob("C","O","-","-","O","-"), False, "Must be unique portfolio identifier"),
    (58, "Action type", "Type of action being reported", "NEWT, MODI, VALU, COLU, EROR, CORR, ETRM, POSC", ob("M","M","M","M","M","M"), False, "Must be a valid action type"),
    (59, "Level", "Trade or position level", "TCTN or PSTN", ob("M","-","-","-","-","-"), False, "Must be TCTN or PSTN"),
    (60, "Collateral market value", "Market value of the collateral", "Decimal amount", ob("C","O","-","-","O","M"), False, "Must be a positive numeric amount"),
    (61, "Currency of collateral market value", "Currency of collateral market value", "ISO 4217", ob("C","O","-","-","O","M"), False, "Must be valid ISO 4217 code"),
    (62, "Haircut or margin", "Collateral haircut or margin percentage", "Decimal (percentage)", ob("C","O","-","-","O","-"), False, "Must be a valid percentage"),
    (63, "Collateral quantity or nominal amount", "Quantity or nominal of collateral", "Decimal", ob("C","O","-","-","O","M"), False, "Must be a positive number"),
    (64, "Currency of collateral nominal amount", "Currency of collateral nominal", "ISO 4217", ob("C","O","-","-","O","C"), False, "Must be valid ISO 4217 code"),
    (65, "Price per unit", "Price per unit of collateral", "Decimal", ob("C","O","-","-","O","C"), False, "Must be a positive number"),
    (66, "Currency of price per unit", "Currency of collateral price", "ISO 4217", ob("C","O","-","-","O","C"), False, "Must be valid ISO 4217 code"),
    (67, "Maturity date of the security (collateral)", "Maturity date of collateral security", "ISO 8601 date", ob("C","O","-","-","O","-"), False, "Must be valid date"),
    (68, "Jurisdiction of the issuer (collateral)", "Jurisdiction of collateral issuer", "ISO 3166-1 alpha-2", ob("C","O","-","-","O","-"), False, "Must be valid country code"),
    (69, "LEI of the issuer (collateral)", "LEI of the collateral issuer", "ISO 17442 LEI", ob("C","O","-","-","O","-"), False, "Must be valid LEI"),
    (70, "Collateral component type", "Type of collateral: security, cash, commodity", "SECU, CASH, COMM", ob("C","O","-","-","O","M"), False, "Must be SECU, CASH, or COMM"),
    (71, "Cash collateral amount", "Amount of cash as collateral", "Decimal amount", ob("C","O","-","-","O","C"), False, "Must be positive if populated"),
    (72, "Cash collateral currency", "Currency of cash collateral", "ISO 4217", ob("C","O","-","-","O","C"), False, "Must be valid ISO 4217 code"),
    (73, "Identification of the security (collateral)", "ISIN of collateral security", "ISO 6166 ISIN", ob("C","O","-","-","O","C"), False, "Must be valid ISIN"),
    (74, "Classification of the security (collateral)", "CFI code of collateral security", "ISO 10962 CFI", ob("C","O","-","-","O","-"), False, "Must be valid 6-char CFI code"),
    (75, "Base product (collateral)", "Base product for commodity collateral", "Enumerated commodity codes", ob("C","O","-","-","O","-"), False, "Required if collateral is commodity"),
    (76, "Sub product (collateral)", "Sub product for commodity collateral", "Enumerated commodity codes", ob("C","O","-","-","O","-"), False, "Required if field 75 populated"),
    (77, "Further sub product (collateral)", "Further sub product for commodity collateral", "Enumerated commodity codes", ob("C","O","-","-","O","-"), False, "Required if field 76 populated"),
    (78, "Collateral quality", "Credit quality of collateral", "INVG, NIVG, NOTR, NOAP", ob("C","O","-","-","O","-"), False, "Must be INVG, NIVG, NOTR or NOAP"),
    (79, "Settlement venue", "MIC of settlement venue for collateral", "ISO 10383 MIC", ob("C","O","-","-","O","-"), False, "Must be valid MIC code"),
    (80, "Rate variance", "Variance from benchmark rate", "Decimal (basis points)", ob("C","O","-","-","O","-"), False, "Must be numeric decimal"),
    (81, "Rate type", "Fixed or floating rate", "FIXD or FLOT", ob("C","O","-","-","O","-"), False, "Must be FIXD or FLOT"),
    (82, "Adjusted rate", "Adjusted lending or repo rate", "Decimal (percentage)", ob("C","O","-","-","O","-"), False, "Must be numeric"),
    (83, "Rate date", "Date of the rate", "ISO 8601 date", ob("C","O","-","-","O","-"), False, "Must be valid date"),
    (84, "Principal amount on value date (Leg 2)", "Principal for second leg of BSB", "Decimal amount", ob("-","-","-","-","-","-",bsb_newt="M",bsb_modi="O",bsb_corr="O"), False, "Must be positive for BSB"),
    (85, "Principal amount currency (Leg 2)", "Currency of second leg for BSB", "ISO 4217", ob("-","-","-","-","-","-",bsb_newt="M",bsb_modi="O",bsb_corr="O"), False, "Must be valid ISO 4217 for BSB"),
    (86, "Security identifier (Leg 2)", "ISIN for second leg of BSB", "ISO 6166 ISIN", ob("-","-","-","-","-","-",bsb_newt="C",bsb_modi="O",bsb_corr="O"), False, "Must be valid ISIN for BSB leg 2"),
    (87, "Type of collateral component (Leg 2)", "Collateral type for second leg of BSB", "SECU, CASH, COMM", ob("-","-","-","-","-","-",bsb_newt="C",bsb_modi="O",bsb_corr="O"), False, "Must be SECU, CASH, or COMM"),
    (88, "Uncollateralised SL flag", "Whether SL is uncollateralised", "Boolean", ob("-","-","-","-","-","-",sl_newt="C",sl_modi="O",sl_corr="O"), False, "Must be true or false"),
    (89, "Termination optionality (SL)", "Termination optionality for SL", "EGRN, ETSB, NOAP", ob("-","-","-","-","-","-",sl_newt="C",sl_modi="O",sl_corr="O"), False, "Must be EGRN, ETSB, or NOAP"),
    (90, "Net exposure collateralisation", "Whether net exposure collateralisation applies", "Boolean", ob("C","O","-","-","O","-"), False, "Must be true or false"),
    (91, "Margin currency", "Currency of the initial margin", "ISO 4217", ob("C","O","-","-","O","-"), False, "Must be valid ISO 4217 code"),
    (92, "Initial margin type", "Distinct or bundled margin", "Enumerated", ob("C","O","-","-","O","-"), False, "Must be valid margin type"),
    (93, "Other type of collateral", "Free text for other collateral types", "Free text (max 35 chars)", ob("C","O","-","-","O","-"), False, "Max 35 characters"),
    (94, "Concentration limit", "Whether a concentration limit applies", "Boolean", ob("O","O","-","-","O","-"), False, "Must be true or false"),
    (95, "Funding sources", "Whether securities obtained through SFT for on-lending", "Enumerated", ob("O","O","-","-","O","-"), False, "Must be from allowed list"),
    (96, "Trading venue of the security", "MIC of venue where security is traded", "ISO 10383 MIC", ob("C","O","-","-","O","-"), False, "Must be valid MIC code"),
    (97, "Mark to market valuation", "Mark-to-market value of outstanding SFT", "Decimal amount", ob("C","O","-","-","O","M"), False, "Must be numeric"),
    (98, "Mark to market currency", "Currency of mark-to-market value", "ISO 4217", ob("C","O","-","-","O","M"), False, "Must be valid ISO 4217 code"),
    (99, "CFI code of the security", "CFI code of the underlying security", "ISO 10962 CFI", ob("C","O","-","-","O","-"), False, "Must be valid 6-char CFI code"),
]
for num, name, desc, fmt, obl, mirror, rule in t2:
    fields.append({"table":2,"number":num,"name":name,"description":desc,"format":fmt,"obligation":obl,"is_mirror":mirror,"validation_rule":rule})

# TABLE 3: Margin Data (20 fields)
t3 = [
    (1, "Type of margin transaction", "Whether margin is posted or received", "MRGG or MRGE", ob("M","O","-","-","O","M"), True, "Must be MRGG or MRGE. Mirror field."),
    (2, "Excess collateral posted", "Value of collateral posted in excess", "Decimal amount", ob("C","O","-","-","O","C"), False, "Must be positive numeric"),
    (3, "Currency of excess collateral posted", "Currency of excess collateral posted", "ISO 4217", ob("C","O","-","-","O","C"), False, "Must be valid ISO 4217"),
    (4, "Excess collateral received", "Value of collateral received in excess", "Decimal amount", ob("C","O","-","-","O","C"), False, "Must be positive numeric"),
    (5, "Currency of excess collateral received", "Currency of excess collateral received", "ISO 4217", ob("C","O","-","-","O","C"), False, "Must be valid ISO 4217"),
    (6, "Initial margin posted", "Value of initial margin posted", "Decimal amount", ob("C","O","-","-","O","C"), False, "Must be positive numeric"),
    (7, "Currency of initial margin posted", "Currency of initial margin posted", "ISO 4217", ob("C","O","-","-","O","C"), False, "Must be valid ISO 4217"),
    (8, "Initial margin received", "Value of initial margin received", "Decimal amount", ob("C","O","-","-","O","C"), False, "Must be positive numeric"),
    (9, "Currency of initial margin received", "Currency of initial margin received", "ISO 4217", ob("C","O","-","-","O","C"), False, "Must be valid ISO 4217"),
    (10, "Variation margin posted", "Value of variation margin posted", "Decimal amount", ob("C","O","-","-","O","C"), False, "Must be positive numeric"),
    (11, "Currency of variation margin posted", "Currency of variation margin posted", "ISO 4217", ob("C","O","-","-","O","C"), False, "Must be valid ISO 4217"),
    (12, "Variation margin received", "Value of variation margin received", "Decimal amount", ob("C","O","-","-","O","C"), False, "Must be positive numeric"),
    (13, "Currency of variation margin received", "Currency of variation margin received", "ISO 4217", ob("C","O","-","-","O","C"), False, "Must be valid ISO 4217"),
    (14, "Short sell indicator", "Whether lent security used for short selling", "Boolean", ob("-","-","-","-","-","-",sl_newt="C",sl_modi="O",sl_corr="O",sl_valu="C"), False, "Must be true or false, SL only"),
    (15, "Total value of margin posted", "Total value of all margin posted", "Decimal amount", ob("C","O","-","-","O","C"), False, "Must be positive numeric"),
    (16, "Currency of total margin posted", "Currency of total margin posted", "ISO 4217", ob("C","O","-","-","O","C"), False, "Must be valid ISO 4217"),
    (17, "Total value of margin received", "Total value of all margin received", "Decimal amount", ob("C","O","-","-","O","C"), False, "Must be positive numeric"),
    (18, "Currency of total margin received", "Currency of total margin received", "ISO 4217", ob("C","O","-","-","O","C"), False, "Must be valid ISO 4217"),
    (19, "Margin lending provided to counterparty", "Margin lending amount provided", "Decimal amount", ob("-","-","-","-","-","-",ml_newt="C",ml_modi="O",ml_corr="O",ml_valu="C"), False, "Must be positive numeric, ML only"),
    (20, "Currency of margin lending", "Currency of margin lending", "ISO 4217", ob("-","-","-","-","-","-",ml_newt="C",ml_modi="O",ml_corr="O",ml_valu="C"), False, "Must be valid ISO 4217, ML only"),
]
for num, name, desc, fmt, obl, mirror, rule in t3:
    fields.append({"table":3,"number":num,"name":name,"description":desc,"format":fmt,"obligation":obl,"is_mirror":mirror,"validation_rule":rule})

# TABLE 4: Re-use Data (18 fields)
t4 = [
    (1, "Collateral re-use", "Whether collateral has been reused", "Boolean", ob("C","O","-","-","O","-"), False, "Must be true or false"),
    (2, "Estimated reuse of collateral", "Estimated value of collateral reused", "Decimal amount", ob("C","O","-","-","O","-"), False, "Must be positive numeric"),
    (3, "Currency of estimated reuse", "Currency of the estimated reuse", "ISO 4217", ob("C","O","-","-","O","-"), False, "Must be valid ISO 4217"),
    (4, "Reinvested cash amount", "Amount of cash collateral reinvested", "Decimal amount", ob("C","O","-","-","O","-"), False, "Must be positive numeric"),
    (5, "Currency of reinvested cash", "Currency of reinvested cash", "ISO 4217", ob("C","O","-","-","O","-"), False, "Must be valid ISO 4217"),
    (6, "Reinvested cash rate of return", "Rate of return on reinvested cash", "Decimal (percentage)", ob("C","O","-","-","O","-"), False, "Must be numeric decimal"),
    (7, "Reinvestment type", "Type of reinvestment of cash collateral", "MMFT, OTHR, REPO, SDPU, SSEC", ob("C","O","-","-","O","-"), False, "Must be MMFT, OTHR, REPO, SDPU, or SSEC"),
    (8, "Reinvestment maturity date", "Maturity date of the reinvestment", "ISO 8601 date", ob("C","O","-","-","O","-"), False, "Must be valid date"),
    (9, "Reinvestment ISIN", "ISIN of the reinvestment security", "ISO 6166 ISIN", ob("C","O","-","-","O","-"), False, "Must be valid ISIN"),
    (10, "Reinvestment cash amount (component)", "Amount reinvested in each component", "Decimal amount", ob("C","O","-","-","O","-"), False, "Must be positive numeric"),
    (11, "Currency of reinvestment (component)", "Currency of each reinvestment component", "ISO 4217", ob("C","O","-","-","O","-"), False, "Must be valid ISO 4217"),
    (12, "Funding source type", "Type of funding used to finance SFT", "Enumerated", ob("O","O","-","-","O","-"), False, "Must be from allowed list"),
    (13, "Funding source market value", "Market value of the funding source", "Decimal amount", ob("O","O","-","-","O","-"), False, "Must be positive numeric"),
    (14, "Currency of funding source", "Currency of the funding source", "ISO 4217", ob("O","O","-","-","O","-"), False, "Must be valid ISO 4217"),
    (15, "Counterparty for reuse", "LEI of counterparty for collateral reuse", "ISO 17442 LEI", ob("C","O","-","-","O","-"), False, "Must be valid LEI"),
    (16, "Type of collateral reuse", "How collateral was reused", "Enumerated", ob("C","O","-","-","O","-"), False, "Must be from allowed list"),
    (17, "Reinvestment risk profile", "Risk profile of the reinvestment", "Enumerated", ob("C","O","-","-","O","-"), False, "Must be from allowed list"),
    (18, "Haircut or margin on reinvestment", "Haircut or margin on reinvestment", "Decimal (percentage)", ob("C","O","-","-","O","-"), False, "Must be valid percentage"),
]
for num, name, desc, fmt, obl, mirror, rule in t4:
    fields.append({"table":4,"number":num,"name":name,"description":desc,"format":fmt,"obligation":obl,"is_mirror":mirror,"validation_rule":rule})

os.makedirs("app/data", exist_ok=True)
with open("app/data/sftr_fields.json", "w") as f:
    json.dump(fields, f, indent=2)

print(f"Generated {len(fields)} fields")
print(f"Table 1: {sum(1 for f in fields if f['table']==1)}")
print(f"Table 2: {sum(1 for f in fields if f['table']==2)}")
print(f"Table 3: {sum(1 for f in fields if f['table']==3)}")
print(f"Table 4: {sum(1 for f in fields if f['table']==4)}")
