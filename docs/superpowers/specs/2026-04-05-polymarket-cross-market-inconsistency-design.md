# Polymarket Cross-Market Inconsistency System Design

## 1. Product Boundary and Success Definition

### Product goal
The long-term goal of this project is to make money with a profitable live trading system on Polymarket.

The first system, however, is not a live trading bot. It is a profit-seeking trading system built with research discipline:
- discover tradeable pricing inconsistencies across related Polymarket markets
- execute those opportunities through honest automated paper trading
- measure which market segments, relationship types, and execution assumptions actually preserve edge after fees, slippage, and decay

### What the first version is
The first version is a discovery-first platform focused on:
- broad market ingestion
- relationship discovery across markets
- inconsistency scoring
- automated paper portfolio management
- analytics and filtering

### What the first version is not
The first version explicitly excludes:
- real-money trading
- full live automation
- NLP-heavy news parsing
- complex forecasting models

### Success definition
The initial system is successful if it can produce evidence for one or more of the following:
- certain relation types show positive expectancy after realistic execution assumptions
- some market segments can be eliminated based on data rather than intuition
- some narrow sub-universes remain attractive after fillability, decay, spread, fee, and slippage effects are included

### Promotion rule
Live automation is not unlocked by intent alone. It is unlocked only after paper results and operational reliability demonstrate that a narrow strategy subset is worth promoting.

## 2. Core System Architecture

The system is composed of seven focused layers.

### 2.1 Market Universe Layer
This layer gathers the tradeable market universe from Polymarket and produces a filtered candidate set for downstream processing.

Inputs gathered:
- market metadata
- outcome structure
- close time
- volume and spread snapshots
- price snapshots
- order book depth when available

Responsibilities:
- discover markets worth monitoring
- remove obviously non-tradeable or stale markets early
- provide a consistent source universe for normalization

### 2.2 Normalization Layer
This layer converts raw market data into a stable internal schema so upper layers are not tightly coupled to exchange-specific response shapes.

Normalized fields include:
- canonical market id
- canonical outcome set
- normalized yes/no pricing
- liquidity features
- timestamps
- event and theme tags

Responsibilities:
- hide Polymarket API and format differences from the rest of the system
- provide a single internal representation for market, quote, and liquidity data
- support consistent downstream scoring and analytics

### 2.3 Relationship Engine
This layer links markets that may have logical or thematic dependence.

Initial relationship families:
- hard-constraint and mutually exclusive relationships
- same-theme correlated relationships

Future extension:
- parent-child and more structured graph relationships

Each relationship record must include:
- relation type
- confidence
- why linked
- semantic risk score

Responsibilities:
- produce explainable cross-market links
- separate high-confidence structural relationships from weaker heuristic ones
- provide the basis for mispricing detection and later graph-based reasoning

### 2.4 Signal Engine
This layer scores detected inconsistencies and ranks opportunities.

The first version uses a rule-based scoring model built from:
- expected consistency band
- observed deviation
- liquidity and spread penalties
- semantic confidence adjustment
- urgency and decay estimate

Responsibilities:
- translate relationships plus current prices into ranked opportunities
- return an explainability payload showing why an opportunity scored the way it did
- support later extension to graph-consistency scoring without changing downstream consumers

### 2.5 Paper Execution Engine
This layer performs realistic simulated execution instead of merely raising alerts.

Responsibilities:
- entry logic
- exit logic
- fee and slippage assumptions
- fill model
- holding window management
- stop conditions
- capital allocation

The paper engine must optimize for honesty over optimism. If a trade is not realistically fillable under the configured assumptions, the engine should avoid counting it as a clean opportunity capture.

### 2.6 Research and Analytics Layer
This layer records the full path from signal generation to trade outcome and segment-level performance.

It stores:
- why a signal was emitted
- which relationship triggered it
- whether a paper trade was opened
- how the trade exited
- how each segment and relation type performed

Responsibilities:
- support post-hoc analysis of edge quality
- identify false positives and fragile strategy classes
- answer the core business question: where does real profit potential actually exist?

### 2.7 Risk Control Layer
This layer constrains the system from the start, even in paper mode.

Required controls:
- maximum concurrent paper positions
- per-market exposure cap
- stale data rejection
- liquidity floor
- spread ceiling
- duplicate opportunity suppression
- global kill switch

Responsibilities:
- stop low-quality or unsafe paper behavior from distorting analytics
- enforce basic operational discipline before any live transition is considered

## 3. High-Value MVP Scope

### MVP objective
The first MVP should answer a narrow and valuable question:

> Can we detect inconsistencies across related Polymarket markets and paper trade them in a way that is realistic enough to evaluate whether an edge exists?

### MVP scope

#### A. Ingestion
- Polymarket market list
- basic market metadata
- current prices
- basic liquidity and spread data

#### B. Normalization
- one market schema
- one outcome schema
- normalized time and liquidity fields
- segment and category labels

#### C. Relationship Engine v1
Only two relationship families are required in the MVP:
1. hard-constraint or mutually exclusive relationships
2. same-theme correlated heuristics

#### D. Signal Engine v1
- rule-based inconsistency score
- explainability payload
- ranked opportunity list

#### E. Paper Execution v1
- automatic paper entries
- basic fill approximation
- time-based and signal-based exits
- fee and slippage model

#### F. Analytics v1
- signal log
- trade log
- segment PnL
- relation-type PnL
- hold-time analysis
- false-positive review set

### Explicitly out of scope for MVP
- live execution
- dashboard as a hard requirement
- graph optimizer in v1
- machine learning models
- news parsing
- a wide strategy library

### MVP success criteria
The MVP is useful if it can establish at least several of the following:
- some relation types are clearly low quality and should be discarded
- some market segments generate better signal quality than others
- fillability is acceptable under realistic assumptions
- decay is measurable and segment-dependent
- a few narrow sub-universes show promising expectancy

## 4. Promotion Logic from Discovery to Live Trading

Live progression happens by crossing evidence thresholds, not by ambition alone.

### Stage 1 — Discovery only
The system produces opportunities and relationship intelligence, but makes no trade-performance claims.

### Stage 2 — Full paper execution
The system opens and closes paper positions according to its own rules.

At this stage the main questions are:
- is there any real edge?
- are opportunities fillable?
- how fast does the edge decay?
- which segments actually work?

### Stage 3 — Semi-automated live trading
The system proposes trades, but final human approval is still required.

This stage measures:
- how much paper results differ from live behavior
- how bad real slippage and market impact are
- whether operational reliability is good enough for automation

### Stage 4 — Narrow live automation
Automation is only allowed in a small, proven slice of the strategy space, under all of the following conditions:
- one or a few validated segments only
- low position sizing
- strict risk limits
- immediate kill switch capability
- acceptable paper-vs-live divergence

### Mandatory evidence before live automation
Before full automation is considered, the system must show:
- sufficient sample size
- positive results by relation type
- positive results after liquidity effects
- positive results after spread and fees
- stable infrastructure
- low incident rate
- an explainable failure taxonomy

### Guiding principle
There should be no broad-universe automation. The system should first identify:
- the best-performing segment
- the best-performing relation type
- the best-performing holding window

Only then should live deployment be considered, and only inside that narrow validated region.

## 5. Recommended Initial Project Structure

The first implementation plan should preserve strict separation between concerns. The codebase should likely evolve around these bounded modules:
- ingestion
- normalization
- relationships
- signals
- paper execution
- analytics
- risk controls
- shared domain models and storage

This boundary structure matters more than the exact package names. The goal is to keep each unit understandable, testable, and replaceable.

## 6. Data Flow Summary

The intended end-to-end flow is:
1. ingest raw Polymarket markets and quote data
2. normalize them into one internal schema
3. infer cross-market relationships
4. compute inconsistency scores and explanations
5. filter opportunities through risk rules
6. simulate entries and exits in the paper portfolio
7. log every decision and outcome for later analysis
8. aggregate analytics by segment, relation type, and holding behavior
9. use evidence to narrow the strategy universe before any live transition

## 7. Error Handling and Operational Rules

The system should prefer dropping bad observations over inventing certainty.

Operational rules:
- reject stale quotes and stale books
- reject opportunities below the configured liquidity floor
- reject opportunities above the configured spread ceiling
- suppress duplicate opportunities generated from the same underlying setup
- preserve full explainability for why a signal or trade was accepted or rejected
- fail closed for paper execution decisions when required market state is missing

## 8. Testing Strategy

The first implementation plan should include tests that validate the key truth-preserving behaviors of the system:
- normalization produces stable canonical market records from raw Polymarket payloads
- relationship inference emits the correct relation type and confidence metadata for known fixtures
- signal scoring applies penalties and adjustments deterministically
- paper execution respects fill, fee, slippage, holding, and stop assumptions
- risk controls suppress trades that violate freshness, liquidity, spread, and duplication rules
- analytics can reconstruct why a signal was emitted and how a trade resolved

The early test suite should rely on deterministic fixtures and scenario-based simulations rather than broad integration ambition.

## 9. Recommended Next Step

The next step is not implementation yet. The next step is to turn this design into a concrete implementation plan for the MVP, with phases that preserve the product boundary:
- discovery-first
- paper-trading only
- analytics-rich
- no live capital until evidence supports promotion
