# Settlement Rulers System

This document describes the settlement rulers system, which adds NPC rulers to each settlement with unique characteristics that influence their governance style.

## Overview

Each settlement in the game can have a ruler NPC who is responsible for making decisions that affect the settlement's development. Rulers have various characteristics that determine their governing style, priorities, and decision-making tendencies.

## Ruler Characteristics

Rulers have several focus areas that influence their decisions:

1. **Expansion Focus (0-100)**
   - High values mean the ruler prioritizes territorial expansion
   - Affects willingness to establish new outposts, claim territory, and build infrastructure

2. **Wealth Focus (0-100)**
   - High values mean the ruler prioritizes accumulating wealth
   - Affects tax rates, trade policies, and resource exploitation

3. **Happiness Focus (0-100)**
   - High values mean the ruler prioritizes citizen happiness
   - Affects public services, festivals, and quality of life investments

4. **Magic Focus (0-100)**
   - High values mean the ruler prioritizes magical development
   - Affects investment in magical research, arcane infrastructure, and mystical alliances

5. **Military Focus (0-100)**
   - High values mean the ruler prioritizes military strength
   - Affects defense infrastructure, training facilities, and military recruitment

6. **Innovation Focus (0-100)**
   - High values mean the ruler prioritizes technological advancement
   - Affects research institutions, crafting facilities, and experimental projects

## Ruler Traits

Rulers also have personality traits and governance styles:

1. **Governing Style**
   - Includes styles like Authoritarian, Democratic, Meritocratic, etc.
   - Affects policy implementation and reaction to events

2. **Personality Traits**
   - Multiple traits like Ambitious, Cautious, Charismatic, etc.
   - Influences decision-making and diplomatic relations

3. **Priorities**
   - Key areas of focus such as Military, Commerce, Education, etc.
   - Guides development decisions and resource allocation

4. **Background**
   - Origin story like Noble Birth, Military, Academic, etc.
   - Provides historical context and influences relationships

## Implementation

Rulers are implemented using several interconnected database tables:

1. **Characters** - Basic identity information
2. **NPCs** - NPC-specific details including stats and skills
3. **CharacterRole** - Assigns the ruler role with custom attributes
4. **Role** - Defines the ruler role and its attribute schema

Each ruler is assigned to a settlement via the `owner_character_id` field in the Settlements table.

## Using the Ruler System

### Creating Rulers

To create rulers for settlements that don't have one:

```bash
python utils/create_settlement_rulers.py
```

This script will:
- Create a "ruler" role if it doesn't exist
- Generate a unique ruler for each settlement without one
- Assign random but suitable characteristics
- Update settlements to link to their new rulers

### Viewing Rulers

To view all settlements and their rulers:

```bash
python utils/list_settlement_rulers.py
```

This displays detailed information including:
- Settlement details
- Ruler name and title
- Ruler characteristics and focus areas
- Governing style and personality traits
- Skills and base stats

### In Game Mechanics

Rulers influence various aspects of gameplay:

1. **Settlement Development**
   - Rulers with high expansion focus may trigger new building projects
   - Military-focused rulers prioritize defensive structures

2. **Diplomatic Relations**
   - Ruler personality affects relationships with other settlements
   - Diplomatic influence determines success in negotiations

3. **Event Responses**
   - Different rulers will respond differently to the same events
   - Governing style affects response to crises and opportunities

4. **Resource Allocation**
   - Focus areas determine where settlement resources are invested
   - Wealth vs. happiness focus balances taxation and public services

## Extending the System

The ruler system can be extended in several ways:

1. **Ruler Progression**
   - Rulers can gain experience and improve their skills over time
   - Governance choices can shift focus areas and traits

2. **Dynasty System**
   - Rulers can age, have successors, and form dynasties
   - Succession crises and power transitions

3. **Political Factions**
   - Multiple power groups within settlements with competing agendas
   - Rulers must balance faction interests

4. **Player Interaction**
   - Players can influence, assist, or oppose ruler decisions
   - Opportunity to depose rulers or become rulers themselves

5. **AI Decision Making**
   - Ruler characteristics can feed into AI systems for autonomous decision making
   - MCTS or other algorithms can use ruler traits as weights in decision processes