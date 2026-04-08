# BrickLink Arbitrage & Valuation Tool

This project aims to leverage real-time sales data from the BrickLink marketplace to develop a sophisticated tool for evaluating the true market value and expected return of LEGO parts and complete sets. Unlike static averages, this tool will incorporate sales volume and distribution analysis for more accurate investment predictions.

## 1. Motivation (The Problem)

Sellers on the marketplace BrickLink primarily use the "Price Guide," which provides an average of the sold price of parts over the last six months.

This simple average is insufficient for serious valuation and arbitrage because it **does not take into account:**

* **Availability and Demand:** The quantity sold in the last six months (sales volume) is crucial. Popular parts sell quickly (high demand), while rare unpopular parts may sell slowly or infrequently (low demand), distorting the average price's reliability.

* **Price Volatility:** A simple average smooths out the distribution, failing to capture price floors, ceilings, and true market risk.

This tool aims to move beyond simple averages by analyzing the full distribution of sales for data-driven decisions.

## 2. Project Roadmap

The project is structured into three main phases: Data Acquisition, Data Analysis, and Application/Deployment.

### Phase 1: Data Scraping & Ingestion

| **Sub-task** | **Description** | **Current Status** | **Tools** | 
 | ----- | ----- | ----- | ----- | 
| **Data Scraping** | Uses Selenium in headless mode to navigate to the BrickLink Price Guide and extract the "Past 6 Months Sales" transaction table data for specific parts and colors. | **Complete** (`bricklink_scraper.py` is functional) | Python, Selenium, Pandas | 
| **Data Ingestion** | Store the structured sales data (Date, Quantity, Price, Condition, Country) into a persistent, structured database for large-scale query and analysis. | **Planned** | PostgreSQL, Psycopg2 (Python adapter) | 

### Phase 2: Core Data Analysis & Statistics

#### 2.1 Calculation of Data Distribution of Sales

After ingestion, the core data processing will involve normalizing the raw sales price data by currency and condition (New/Used) to calculate a more robust valuation metric.

* **Goal:** For every part/color combination, calculate the **Probability Density Function (PDF)** of the sold price per unit.

* **Technique:** Use Kernel Density Estimation (KDE) or fit the data to a known distribution (e.g., Log-Normal or Weibull distribution, as prices are positive and often skewed).

#### 2.2 Computation of Statistics: Expected Return Value

This is the key output of the project. Given a LEGO set number, we want to calculate the **Expected Return Value ($\mathbb{E}[R]$)** of parting it out in the next 24 months.

* **Formula:** The expected value of a set's parts is the sum of expected values of its individual parts.

$$
\mathbb{E}[R_{Set}] = \sum_{i \in Set} \mathbb{E}[R_{Part_i}]
$$

* **Expected Value of a Part ($\mathbb{E}[R_{Part}]$):** This is calculated as the average price of the part weighted by its sales frequency (derived from the distribution).

* **Risk and Volatility:** We will also compute the standard deviation ($\sigma$) of the price distribution to provide a **risk assessment** for the set's return.

### Phase 3: Deployment

| **Sub-task** | **Description** | **Status** | **Tools** | 
 | ----- | ----- | ----- | ----- | 
| **Deployment & Scheduling** | Deploy the scraper and analysis script to a continuous server environment to run daily/weekly. | **Planned** | Docker, AWS Fargate / Google Cloud Run | 
| **User Interface** | Develop a simple web interface where a user can input a Set ID and see the calculated Expected Return Value, $\sigma$, and the top five most valuable parts. | **Planned** | Python Flask/Django or Streamlit | 

## 3. Setup and Usage

### Prerequisites

* Python 3.x

* Selenium

* A dedicated version of Chrome (e.g., Chrome for Testing v141) and the matching ChromeDriver v141.

### Quick Start

1. **Clone the repository:**