import logging as logger

class Inventory:
    """
    Represents the inventory of a player or npc.
    This includes items that the player is carrying.
    """
    def __init__(self):
        self.items = []
        self.capacity = 20
        logger.info(f"Inventory created for {self.player.name}")

    
    def add_item(self, item):
        """
        Add an item to the player's inventory.
        
        Args:
            item (str): The name of the item
        """
        self.items.append(item)
        self._dirty = True
        logger.info(f"Added item to inventory: {item}")

    def remove_item(self, item):
        """
        Remove an item from the player's inventory.
        
        Args:
            item (str): The name of the item
        """
        if item in self.items:
            self.items.remove(item)
            self._dirty = True
            logger.info(f"Removed item from inventory: {item}")
        else:
            logger.warning(f"Failed to remove item from inventory: {item} not found")

    def upgrade_capacity(self, capacity):
        """
        Upgrade the capacity of the player's inventory.
        
        Args:
            capacity (int): The new capacity of the inventory
        """
        self.capacity = capacity
        self._dirty = True
        logger.info(f"Upgraded inventory capacity to: {capacity}")

    def __str__(self):
        """
        Returns a user-friendly string representation of the inventory.
        This is intended for displaying the inventory contents in a readable format.
        """
        return f"Inventory: {self.items}, Capacity: {self.capacity}"
    
    def __repr__(self):
        """
        Returns an unambiguous string representation of the inventory.
        This is intended for debugging and should ideally allow recreating the object.
        """
        return f"Inventory({self.items}, {self.capacity})"
    
    def __eq__(self, other):
        if isinstance(other, Inventory):
            return self.items == other.items and self.capacity == other.capacity