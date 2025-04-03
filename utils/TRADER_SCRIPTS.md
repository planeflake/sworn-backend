# Trader Management Scripts

This directory contains scripts for managing traders in the Sworn backend.

## Adding New Traders

### Using Python Script

The `add_traders.py` script creates 5 new NPCs with trading skills and their corresponding trader records.

To run the script:

```bash
cd sworn-backend
python utils/add_traders.py
```

The script will:
1. Find the first world in the database (or create one if none exists)
2. Find the first settlement (or create one if none exists)
3. Create 5 trader NPCs with unique skills and personalities
4. Create corresponding trader records linked to those NPCs

### Using SQL Script

Alternatively, you can run the SQL script directly against your PostgreSQL database:

```bash
cd sworn-backend
psql -d sworn -U postgres -f add_traders.sql
```

## Trader Profiles

The scripts create the following traders:

1. **Orrin Silverhand** - Master Trader
   - High trading and negotiation skills
   - Shrewd but honest
   - Prefers coastal regions
   - Well-protected cart with 3 guards

2. **Lyra Nightshade** - Exotic Goods Specialist
   - Expert at appraising rare items
   - Mysterious and knowledgeable
   - Prefers exotic biomes like jungle and swamp
   - Specialized containers for rare goods

3. **Thorne Ironwood** - Caravan Master
   - Skilled in survival and navigation
   - Brave and practical
   - Travels through plains and forests
   - Large, well-guarded caravan with 5 guards

4. **Milo Quickfoot** - Traveling Peddler
   - Master bargainer
   - Charming and adaptable
   - Operates in urban and coastal areas
   - Light, fast cart for quick escapes

5. **Seraphina Goldweaver** - Trading Consortium Representative
   - Expert in economics and diplomacy
   - Sophisticated and calculating
   - Focuses on urban centers
   - Luxurious, secure cart with diplomatic insignia

## Notes

- Each trader has unique skills, personality traits, and cart upgrades
- Traders are initially placed in the same settlement
- The scripts check for existing entries to avoid duplicates
- Traders are ready to be used in game mechanics, including movement and tasks