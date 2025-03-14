from workers.celery_app import app, get_traders, get_settlement_needs
from random import choice

@app.task
def update_trader_location(trader_name):
    """Move a trader between settlements based on supply and demand"""
    traders = get_traders()
    settlement_needs = get_settlement_needs()
    
    # Find the trader
    trader = next((t for t in traders if t["name"] == trader_name), None)
    if not trader:
        return {"error": f"Trader {trader_name} not found"}
    
    # Current settlement
    current = trader.get("current_location", trader.get("settlement"))
    if not current:
        current = trader["home_settlement"]
        trader["current_location"] = current
    
    # Determine best settlement to move to based on what trader has and settlements need
    best_match = None
    best_score = -1
    
    for settlement, needs in settlement_needs.items():
        if settlement == current:
            continue  # Skip current settlement
            
        match_score = 0
        for item, details in trader["wares"].items():
            if item in needs:
                # Higher score for high urgency items
                urgency_multiplier = {"high": 3, "medium": 2, "low": 1}
                # Higher score when trader price is below settlement max price
                price_match = 1 if details["price"] <= needs[item]["max_price"] else 0.5
                
                match_score += details["quantity"] * urgency_multiplier[needs[item]["urgency"]] * price_match
        
        if match_score > best_score:
            best_match = settlement
            best_score = match_score
    
    if best_match and best_score > 10:  # Only move if good opportunity exists
        trader["settlement"] = best_match
        trader["current_location"] = best_match  # Update both for compatibility
        return {
            "trader": trader_name,
            "moved_to": best_match,
            "reason": f"Found good trading opportunity (score: {best_score})"
        }
    
    return {
        "trader": trader_name, 
        "stayed_at": current,
        "reason": "No better opportunities elsewhere"
    }

@app.task
def update_all_traders():
    """Update all trader positions"""
    traders = get_traders()
    results = []
    
    # Instead of calling .get() which blocks, we'll just spawn tasks and return
    for i, trader in enumerate(traders):
        # Use apply_async with a countdown to stagger task execution
        # This prevents all tasks from executing simultaneously
        update_trader_location.apply_async(
            args=[trader["name"]], 
            countdown=1 * i  # Stagger by 1 second per trader
        )
        results.append(f"Started task for trader {trader['name']}")
    
    return {"status": "Update trader tasks dispatched", "count": len(traders)}

@app.task
def trader_buy_and_sell():
    """Have traders buy and sell based on settlement needs"""
    # Implementation for trade behavior
    traders = get_traders()
    settlement_needs = get_settlement_needs()
    
    results = []
    for trader in traders:
        # Use current_location if available, otherwise settlement
        settlement_name = trader.get("current_location", trader.get("settlement"))
        if not settlement_name:
            settlement_name = trader["home_settlement"]
            
        if settlement_name in settlement_needs:
            needs = settlement_needs[settlement_name]
            
            # Simple implementation: adjust trader wares based on settlement needs
            for item, need_info in needs.items():
                # If trader has this item, potentially sell some
                if item in trader["wares"]:
                    # Higher urgency = sell more
                    urgency_factor = {"high": 0.3, "medium": 0.2, "low": 0.1}
                    sell_quantity = max(1, int(trader["wares"][item]["quantity"] * urgency_factor[need_info["urgency"]]))
                    
                    # Don't sell more than we have
                    sell_quantity = min(sell_quantity, trader["wares"][item]["quantity"])
                    
                    if sell_quantity > 0:
                        trader["wares"][item]["quantity"] -= sell_quantity
                        results.append({
                            "trader": trader["name"],
                            "settlement": settlement_name,
                            "sold": {
                                "item": item,
                                "quantity": sell_quantity,
                                "price": trader["wares"][item]["price"]
                            }
                        })
            
            # Trader buys local resources that are abundant
            # This would depend on settlement data, simplified for now
            
    return results