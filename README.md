# POS Printing system
My attempt at saving a bunch of money by programming a recipt printer by myself instead of buying one.
Specifically, it's an order information sticker which gets printed with each payment to inform the workers what they are making (for a bubble tea stall).

I didn't initally realise the challenges that would come with setting this up, but it is now in use, working reasonably well, definetly saving a lot of money.
It's not perfect, and still needs a few small adjustments soon, but thought I would upload it as it was an interesting project to work on fs.

## Simple explanation:
- Connects with Square API (The POS system in use)
   - requires the developer console to be setup and connected
- Uses ngrok to reroute external traffic onto local device
- Filters down order data in to main information
- Splits up main information into a neat contained structure for simple formatting
- Displays all information on a the sticker (in the desired layout), with some codeification
- has in built handling for order numbers, feeding to next ticket, multiple quanities, multiple items in an order etc.
