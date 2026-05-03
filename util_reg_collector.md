Create a script that can call the gate keeper script to request gates to certain mage shops.

Script will flow as follows: 
    - Scan a static container for quantity of regs.
    - makes a call to gate keeper to gate mage shop 1.
    - Buy all regs that are not in stock.
    - Request a Gate back and unload purchased regs into scanned container.

Let's store that static container in the script as a variable. It is in a primary container so we'll want to ensure that chest is tracked and opened as well. 

If the player doesn't have to move to purchase the regs we are free to purchase up to 500 stones on our inventory. We should make sure that a future purchase won't exceed this weight so nothing is dropped.

