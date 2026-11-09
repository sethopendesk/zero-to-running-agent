import json
from ast import List

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt
from pyasn1.type.univ import Null
from pydantic import BaseModel, Field

from agent import config
from agent.drafting import apply_decisions, save_approved, template_email, send_approved
from agent.llm import get_llm
from agent.log import log_event
from agent.state import AgentState
from pathlib import Path

SYSTEM_FETCH = """Check out these 5 websites and fetch the business listings from each page. 

Blue Ridge Brokerage - https://www.blueridgebrokerage.com/businesses-for-sale/
DealStream - https://dealstream.com/north-carolina/wake-county-businesses-for-sale
Empire Business Brokers - https://www.empirebizbroker.com/businesses-for-sale
Enlign Advisors - https://enlign.com/active
First Choice Business Brokers - https://thetriangle.fcbb.com/businesses-for-sale?sort=FeaturedLocalBusinesses&page=1

Give me a JSON file with a entry for each listing.
Do not group by website.
Each entry in the JSON file must follow this example format and 
have the 'id' field increasing incrementally for each entry:

  {
    "id": int,
    "source": str,
    "source_url": str,
    "title": str,
    "listing_url": str,
    "listing_id": str,
    "status": str,
    "asking_price": str,
    "asking_price_usd": float,
    "location": str,
    "industry": str,
    "annual_revenue_usd": float,
    "cash_flow_usd": float,
    "sde_usd": float,
    "ebitda_usd": float,
    "includes": str,
    "tags": [],
    "notes": str
  }

"""

class FoundListing(BaseModel):
    id: int = Field(
        ge=1, le=1000,
        description="Ordinal number representing the listing's position in the results, starting at 1."
    )

    source: str = Field(
        min_length=1, max_length=1000,
        description="Name of the website or business brokerage hosting the listing."
    )

    source_url: str = Field(
        min_length=3, max_length=1000,
        description="URL of the host website's main business-for-sale listings page."
    )

    title: str = Field(
        min_length=3, max_length=1000,
        description="Exact title of the business-for-sale listing as displayed on the website."
    )

    listing_url: str | None = Field(
        default=None,
        description="Direct URL to the individual business listing page. Null if unavailable."
    )

    listing_id: str | None = Field(
        default=None,
        description="Unique listing identifier assigned by the hosting website or brokerage. Null if unavailable."
    )

    status: str | None = Field(
        default=None,
        description="Current availability status of the listing, such as Active, Sale Pending, Under Contract, or Sold."
    )

    asking_price: str | None = Field(
        default=None,
        description="Asking price exactly as displayed on the website, including currency symbols, ranges, and additional conditions."
    )

    asking_price_usd: float | None = Field(
        default=None, ge=0,
        description="Numeric asking price in US dollars, excluding currency symbols and formatting. Null if the price is unknown, a range, or cannot be reliably determined as a single amount."
    )

    location: str | None = Field(
        default=None,
        description="Geographic location of the business, including city, state, county, or region when provided."
    )

    industry: str | None = Field(
        default=None,
        description="Industry or business category, such as HVAC, Restaurant, Manufacturing, Retail, or Landscaping."
    )

    annual_revenue_usd: float | None = Field(
        default=None, ge=0,
        description="Reported annual gross revenue of the business in US dollars. Null if not disclosed."
    )

    cash_flow_usd: float | None = Field(
        default=None,
        description="Reported annual business cash flow in US dollars, using the listing's terminology. Null if not disclosed."
    )

    sde_usd: float | None = Field(
        default=None,
        description="Reported Seller's Discretionary Earnings (SDE) in US dollars. Null if not disclosed."
    )

    ebitda_usd: float | None = Field(
        default=None,
        description="Reported Earnings Before Interest, Taxes, Depreciation, and Amortization (EBITDA) in US dollars. Null if not disclosed."
    )

    includes: str | None = Field(
        default=None,
        description="Assets included in the advertised sale, such as Business, Real Estate, Business and Real Estate, or Inventory."
    )

    tags: list[str] = Field(
        default_factory=list,
        description="List of special listing attributes explicitly mentioned, such as Seller Financing, Relocatable, Management Will Stay, Price Reduced, or New Arrival."
    )

    notes: str | None = Field(
        default=None,
        description="Additional relevant information, qualifications, uncertainties, or caveats about the listing that are not captured by other fields."
    )

class FoundListings(BaseModel):
    listings: list[FoundListing] = Field(
        description="All business-for-sale listings extracted from the website. Include only information supported by the retrieved page content."
    )


def scrape_node(state: AgentState) -> dict:
    run_id = state["run_id"]

    # Initialize Claude.
    try:
        llm = get_llm()
    except Exception as exc:
        log_event(
            run_id,
            "scrape",
            "init_failed",
            error=str(exc)
        )
        raise RuntimeError(
            "Could not initialize the scraping LLM"
        ) from exc

    # IMPORTANT:
    # This call alone does not provide web access.
    # A web retrieval mechanism must be configured separately.
    try:
        response = llm.with_structured_output(
            FoundListings,
            method="json_schema",
            include_raw=True
        ).invoke([
            SystemMessage(content=SYSTEM_FETCH),
            HumanMessage(
                content=(
                    "Extract business-for-sale listings "
                    "from the supplied website content. "
                    "Do not invent missing information."
                )
            )
        ])

        if response is None:
            raise ValueError("Claude returned no listings response")

        if response["parsed"] is not None:
            # Successfully parsed into your Pydantic model
            listings = response["parsed"].model_dump(mode="json")["listings"]

            print(f"Successfully extracted {len(listings)} listings")

        else:
            # Structured output failed
            print("Claude could not produce valid listing JSON.")

            print("Parsing error:")
            print(response["parsing_error"])

            print("Claude's raw response:")
            print(response["raw"].content)

        # Validate and convert to standard Python data.
        validated = FoundListings.model_validate(response["parsed"])
        listings = validated.model_dump(mode="json")["listings"]

    except Exception as exc:
        log_event(
            run_id,
            "scrape",
            "extraction_failed",
            error=str(exc)
        )
        raise RuntimeError(
            "Business listing extraction failed"
        ) from exc

    # Write a snapshot.
    output_path = config.DEFAULT_LISTINGS
    output_path.parent.mkdir(parents=True, exist_ok=True)
    print("got here")

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            listings,
            file,
            indent=4,
            ensure_ascii=False
        )

    log_event(
        run_id,
        "scrape",
        "completed",
        count=len(listings),
        output_file=str(output_path)
    )

    # Pass listings directly to the next node.
    return {
        "input_listings": listings,
        "listings_source": str(output_path)
    }
