---
name: pantry-to-plate
description: Turns a pantry photo or ingredient list into cheap recipes that fit the student's allergies, diet and budget, and finds the nearby stores with the best prices for anything missing. Use whenever the student sends a photo of their pantry, fridge or groceries, asks what they can cook with what they have, wants cheap or budget meals, asks where groceries are cheapest near them, says they are broke until payday and need food, wants a grocery list or a day of breakfast, lunch and dinner on a budget, asks what their groceries will cost a week, or tells Cubbie about a food allergy, diet, food budget or calorie/nutrition goal to remember, even if they never say "recipe".
---

# Pantry to Plate

Cheap meals from what the student already has. The student sends a photo of their pantry or fridge, or just
lists what they have. Cubbie suggests budget recipes for breakfast, lunch and dinner that respect their
allergies and diet, with the ingredients and what each one costs, checks nearby stores so they know where the
missing items are cheapest, and works out what buying those items every week would cost.

- Inputs: ingredients (a photo or a list), restrictions (allergies and diet), budget, location and an optional
  calorie/nutrition goal. All but the ingredients come from the student's saved food profile, so after the first
  time the student only has to send a photo.
- Outputs, always in this order (see Replies for the exact format):
  1. *Recipes*: breakfast, lunch and dinner, each with its ingredients and a cost estimate.
  2. *Stores Near You*: nearby stores known for low prices on the ingredients still to buy.
  3. Prompts for anything still missing: their location, a pantry photo, or a list of what they have.
  4. *Weekly Budget*: what buying the repeated items every week would cost, against their budget.
  5. *Nutrition Goal*: a prompt for their calorie/nutrition goal, or, once it is saved, how the day's meals
     compare to it.

This Skill uses Cubbie's built-in abilities (reading photos, web search, the browser, background tasks,
documents, scheduled check-ins and, if connected, Google Tasks) plus one small script,
`scripts/food_profile.py`, that saves the student's food profile word for word. The script uses only Python's
standard library, so there is nothing to install, and the Skill needs no sign-in or key.

## When to use

- (a photo of a pantry or fridge) "what can I make with this"
- "I have $15 until Friday, what should I cook?"
- "cheap dinner ideas? all I have is rice, eggs and frozen veggies"
- "where's the cheapest place near me to get chicken and rice?"
- "vegan meals under $4 a serving I can make in a microwave"
- "btw I'm allergic to shellfish"

Do not use it for restaurants, food delivery, the dining hall menu, or medical or weight-loss diet plans. A
calorie or nutrition goal the student sets ('2000 cal a day', 'high protein') is fine to plan toward; don't
suggest one, and point them to a doctor or dietitian for anything medical.

## The student's food profile

Suggesting the wrong food can make someone sick, so the profile lives in a file rather than in Cubbie's general
memory, which can reword details or miss them. The file is `~/.config/pantry-to-plate/profile.json` in the
student's own sandbox. It survives restarts and Skill updates, and nothing in it changes unless one of the
commands below changes it. Allergies and diet rules always win over everything else, including what is in the
photo and what sounds tastiest.

What it holds, with the flag that saves each item:

1. **Allergies and intolerances** (`--allergy`), each with how serious it is: `severe` (even traces) or `avoid`.
   An allergy saved without a severity counts as severe until the student says otherwise. Never suggest a recipe
   that contains one.
2. **Diet rules** (`--diet`): vegetarian, vegan, pescatarian, halal, kosher, gluten-free, dairy-free,
   low-sodium, or anything else they follow.
3. **Dislikes and favorites** (`--dislike`, `--favorite`): foods they won't eat, and foods, cuisines and spice
   levels they love.
4. **Budget** (`--budget`): the amount and what it covers, such as '$5 a meal', '$30 a week' or '$15 until
   Friday'.
5. **Kitchen** (`--kitchen`, `--cook-time`): what they can cook with (microwave, hot plate, stove, oven, air
   fryer, rice cooker) and how long they usually want to spend cooking.
6. **Servings** (`--servings`): just them, shared with roommates, or meal prep for a few days.
7. **Location** (`--location`, `--travel`): a ZIP code or campus name, never a street address (the script
   refuses one), and how they get to the store (walk, bus, bike, car).
8. **Stores** (`--store-like`, `--store-avoid`, `--loyalty-card`): ones they like, can reach or want to avoid,
   and any free loyalty card they already have.
9. **Staples** (`--staple`): what they always keep (oil, salt, spices, rice), so they are never asked again.
10. **Recipe history** (`--liked`, `--disliked`): recipes they liked or didn't; the last 30 of each are kept.
11. **Nutrition goal** (`--nutrition-goal`): the calorie or nutrition target the student gave, word for word,
    such as '2000 cal a day' or 'high protein, 120 g a day'.

### Profile commands

Run these from this Skill's folder. Each prints one JSON object. Put every value in single quotes, because a
dollar sign inside double quotes disappears. For a value with an apostrophe, use double quotes and write money
without the dollar sign ("Trader Joe's", "5 dollars a meal").

| Command | What it does |
| --- | --- |
| `python3 scripts/food_profile.py show` | Reads the profile and changes nothing. Returns `safety_line`, `missing` (what still needs asking, in order) and the full `profile`. |
| `python3 scripts/food_profile.py add --allergy 'shellfish:severe' --diet 'vegetarian'` | Adds items and leaves everything else as it is. Repeat a flag to add several. |
| `python3 scripts/food_profile.py set --budget '$5 a meal' --location '78705'` | Sets single values. A list flag (`--diet 'vegan'`) replaces that one list. |
| `python3 scripts/food_profile.py set --nutrition-goal '2000 cal a day, high protein'` | Saves the calorie/nutrition goal. |
| `python3 scripts/food_profile.py set --no-allergies` | Saves that the student has no allergies. |
| `python3 scripts/food_profile.py set --offer 'weekly-checkin=declined'` | Remembers the answer to a follow-up offer: `weekly-checkin` or `google-tasks`, `accepted` or `declined`. |
| `python3 scripts/food_profile.py remove --dislike 'mushrooms'` | Removes one item. |
| `python3 scripts/food_profile.py remove --allergy 'peanuts' --confirmed` | Removes an allergy, only after the student says yes. |
| `python3 scripts/food_profile.py forget --field 'location'` | Clears one field. |
| `python3 scripts/food_profile.py forget --all --confirmed` | Deletes the whole profile, only after the student says yes. |
| `python3 scripts/food_profile.py --sample show` | Uses the bundled sample, `assets/sample_profile.json`, and saves nothing. For testing. |

After a change, the output includes `confirmation`: a ready-made line that always ends with the allergies on
file, so the student can see they are intact.

| Exit code | Meaning | What to do |
| --- | --- | --- |
| 0 | Done | After saving an allergy, diet, budget, kitchen or location, text the `confirmation` line word for word. |
| 2 | A command or value was rejected; the message says why | Fix the command and run it again. For a street address, ask for a ZIP code or campus instead. |
| 3 | Needs the student's yes: removing or loosening an allergy, or deleting the profile | Ask in one line exactly what will change ("Remove peanuts from your allergies?") and rerun with `--confirmed` only if they say yes. |
| 4 | Not in the profile | Tell the student what is on file and ask what they meant. |
| 5 | The saved profile can't be read | Suggest nothing yet. Ask the student to confirm their allergies and diet again, run `forget --all --confirmed`, then save their answers fresh. |
| 6 | The profile couldn't be saved | Tell the student the change wasn't saved, and don't act as if it was. |

### Keeping it right

- Start every request by running `show`.
- If `missing` starts with `allergies`, ask about allergies before anything else, as its own question: "Before I
  suggest anything: any food allergies or foods you can't eat? Say 'none' if not." Save each one with
  `add --allergy '<item>:<severe or avoid>'`, or save `set --no-allergies`. If they name one without saying how
  serious, save it without a severity and ask once.
- Then ask for whatever else `missing` lists in one text the student can answer in one go: "Quick setup so I get
  it right: budget, diet, what you cook with, and your ZIP. Like: '$5 a meal, vegetarian, microwave + stove,
  78705'". Skip whatever they have already said; the other items can come up naturally later.
- Save only what the student tells you. Never guess an allergy, a diet rule or a dislike from a photo or from
  past choices.
- Save a change as soon as the student mentions it ("I eat meat again", "add shellfish to my allergies"), with
  the smallest command that does it, then text the `confirmation` line.
- If they ask what you remember about their food, send the `safety_line` and the rest of the profile in a few
  short lines. If they ask you to forget something, use `remove` or `forget`.
- If a request clashes with the profile ("make me a peanut stir-fry"), ask whether the profile is out of date or
  the food is for someone else before suggesting anything.
- The file is the source of truth. If Cubbie's memory or the conversation mentions an allergy or diet rule the
  file doesn't have, ask the student whether to add it before suggesting anything.
- Keep the profile on the student's Cubbie and never send it anywhere else. Don't ask about income or why money
  is tight; the budget number is enough.

## Steps

1. **Run `show`.** If allergies are still unknown, ask and save them first: no recipes until they are known.
   Anything else that is missing (location, budget, nutrition goal, ingredients) doesn't hold up the reply: plan
   with what you have and ask for the rest in the reply's prompts. When the student gives any of it, save it
   right away.

2. **Work out the ingredients.**
   - From a photo: read the photo the student sent and list what you can identify, with rough amounts when you
     can see them.
   - If you are not sure what an item is and it could contain one of the allergens on file (a jar that might be
     peanut butter, a bag that might be almond flour), ask before using it. If everything is clear, don't ask;
     list what you saw at the top of the reply so the student can correct it.
   - From a text list: use it as given. With no ingredients at all, plan from scratch within their budget and
     ask for a pantry photo or list in the reply's prompts.
   - Leave out anything that clashes with the profile and say so in a few words ("skipped the peanut butter,
     peanut allergy").
   - If something looks spoiled or moldy, don't plan around it, and mention it kindly.
   - A photo can't show allergen labels or "may contain" warnings. When the student has a severe allergy and a
     recipe uses packaged food, remind them to check the label.

3. **Choose one recipe each for breakfast, lunch and dinner.** If the student asks about only one meal, or for
   more options, give that instead.
   - First rule out anything that breaks an allergy or diet rule, uses something on `dislikes`, needs equipment
     that isn't in `kitchen`, or takes longer than their `cook_time`.
   - Then prefer recipes that use more of what they already have and need fewer things bought, use up
     perishables first (produce, dairy, opened packages), fit the budget, match `favorites`, and weren't
     suggested recently. Bring back `liked_recipes` now and then, and never suggest `disliked_recipes`.
   - Share ingredients across the three meals where it makes sense (eggs at breakfast and in the fried rice), so
     the shopping list stays short.
   - If a nutrition goal is saved, steer toward it (more protein for 'high protein', lighter meals for a lower
     calorie target) without breaking any rule above or the budget.
   - If the budget covers several days ('$15 until Friday'), plan breakfast, lunch and dinner for those days
     and keep the whole shopping list within it. Anything longer than a phone screen goes in a PDF.
   - For a severe allergy, or one saved without a severity, also skip recipes where cross-contact is likely,
     such as bulk-bin ingredients or food fried in shared oil.
   - Simple, well-known recipes work best. When you use a recipe from the web, put its link on its own line and
     write the steps in your own words.

4. **Make the shopping list and cost each recipe.**
   - The list is only what the chosen recipes still need, combined across recipes and with amounts, leaving out
     the student's `staples`. What they already have counts as already paid for.
   - For each recipe, give two numbers: what the student has to spend now (its share of the shopping list) and
     about what it costs a serving, counting a fair share of every ingredient, including what they already
     have. Use the store prices from step 5 when you have them; until then, use typical prices and mark them
     "est.".

5. **Find the best prices nearby.**
   - Search the web for grocery stores near the student's `location` that they can reach by their `travel`:
     about a mile on foot, a few miles by bus or bike, up to about 10 miles by car, unless they've said
     otherwise. Include `stores_like` and skip `stores_avoid`.
   - Check current prices for the shopping list at up to three of those stores. Open each store's own website in
     the browser, set to the nearest location, or read its weekly ad. Delivery apps often charge more than the
     store, so don't use them for prices. Prefer store brands and compare similar sizes.
   - Looking up prices needs no account. Don't create accounts, sign in, fill a cart or clip coupons. If a site
     asks for a sign-in or a check that you're human, skip that store. If a lower price needs a free loyalty
     card or a digital coupon, mention it, especially for a card in `loyalty_cards`.
   - Use only prices you actually found, and say where they came from ("from their site today"). If an item has
     no listed price, say so. A typical price is fine only when it is clearly marked as an estimate; never
     present a guess as a store's price.
   - List up to three of those stores with the total for the shopping list at each, cheapest first, and
     recommend one for the whole list. Suggest splitting the trip only when it saves a few dollars and the
     stores are close together.
   - With no location yet, skip the search: the *Stores Near You* section says it needs their ZIP or campus.
   - If checking prices will take more than a minute or two, send the reply with estimated costs first, run the
     price check as a background task, and text the *Stores Near You* section when it's ready.

6. **Work out the weekly budget.** Assume the student makes these meals for the week (or follows the multi-day
   plan) and repeats the shop every week.
   - List the items they would buy every week, with the weekly amount and price: the shopping list scaled to
     seven days, plus anything from their pantry the week would use up (a dozen eggs gone by Thursday). Leave
     out `staples` and anything that lasts longer than a week, and say so in a few words.
   - Give the weekly total and compare it to the budget turned into a weekly amount ('$5 a meal' is about $105
     a week for three meals a day; '$15 until Friday' covers only those days, so say what a full week would
     take). Say clearly if it goes over, and by how much.
   - Use the same prices as the rest of the reply and keep the "est." marks.

7. **Check the nutrition goal.** If `nutrition_goal` is saved, estimate the day's calories and whatever else the
   goal names (protein, for example) from typical values, mark them as estimates, and say in one line how close
   the day comes. If it isn't saved, ask for it at the end of the reply instead.

8. **Reply** following the Replies section below. Start with the `safety_line`, word for word.

9. **Send the full recipe** when the student picks one, starting with the safety line again: ingredients with
   amounts (marking what they have and what to buy), then four to eight short steps, the time and the number of
   servings. If it is longer than a phone screen, make a one-page PDF recipe card with the safety line at the
   top, send it, and text a one-line summary.

10. **Optional follow-ups.** Offer only what `offers` in the profile has no answer for, one at a time, and save
   the student's answer with `set --offer`.
   - `google-tasks`: add the shopping list to the student's Google Tasks. If Google isn't connected, send the
     list as a text instead.
   - `weekly-checkin`: a weekly pantry check-in. Suggest Sunday at 5 pm and let the student pick the day, the
     time and how often. Create it only after they say yes, in their time zone, and word it so it makes sense
     on its own later: "Pantry to Plate weekly check-in: from the pantry-to-plate Skill's folder, run
     `python3 scripts/food_profile.py show`, text the student their safety line with 'Still right?', then ask
     for a pantry photo or list and suggest this week's budget meals."
   - When the student says how a recipe went, save it with `add --liked '<recipe>'` or
     `add --disliked '<recipe>'`.

## Replies

Every recipe reply has the same five parts, in this order, each sent as its own message:

1. *Recipes*: the `safety_line` word for word, what you saw in the photo, then breakfast, lunch and dinner.
   Each gets its name and time, the ingredients (what they have, then what to buy) and the cost: what they
   spend now and about what it costs a serving. End with "Reply breakfast, lunch or dinner for the full steps."
2. *Stores Near You*: up to three nearby stores with the total for the items to buy, cheapest first, which one
   to go to, and where the prices came from. With no location yet, say you need their ZIP or campus to check.
3. Prompts, with no heading, only for what is still missing: their location, a pantry photo, or a list of what
   they have (and their budget, if none is saved). Ask for all of them in one message, each on its own line.
   Leave this message out when nothing is missing.
4. *Weekly Budget*: the items they'd buy every week with amounts and prices, the weekly total, and how it
   compares to their budget.
5. *Nutrition Goal*: with no goal saved, ask for one. With one saved, the day's estimate against it in one line.

Formatting:

- Plain text, a few short lines per section. The only formatting is the section labels above, written exactly
  as shown (`*Recipes*`, `*Stores Near You*`, `*Weekly Budget*`, `*Nutrition Goal*`). No other headings, bold or
  tables. Use dashes or numbers for lists.
- Every reply that suggests or sends a recipe starts with the `safety_line`, word for word, so the student can
  see what it was checked against. If there is no safety line, ask about allergies instead of suggesting
  anything.
- Lead with the answer. Show money like "$4.85" or "about $1.20 a serving", and mark every estimate "est.".
- Put every link (recipes, stores) on its own line.
- Anything longer than a phone screen, such as a full week of meals, goes in a PDF with a one-line summary in the
  text.

Example texts, for a student who sent a pantry photo and has a ZIP saved but no nutrition goal (so there is no
prompts message):

```text
*Recipes*
Checked against your profile: no peanuts (severe), vegetarian.
From your pic: rice, black beans, eggs, half an onion, frozen spinach.

Breakfast: Spinach egg tacos, 15 min
- Have: eggs, frozen spinach
- Buy: tortillas, salsa
- Cost: $4.14 now, about $1.10 a serving

Lunch: Black bean fried rice, 20 min
- Have: rice, black beans, eggs, onion, frozen spinach
- Buy: nothing
- Cost: $0 now, about $0.90 a serving

Dinner: Bean and rice burrito bowls, 25 min
- Have: rice, black beans, onion, salsa (from breakfast)
- Buy: a lime
- Cost: $0.35 now, about $1.30 a serving

Reply breakfast, lunch or dinner for the full steps.
```

```text
*Stores Near You*
For tortillas, salsa and a lime, by bus:
1. Aldi on Main St, $4.49 (go here)
2. H-E-B on Lamar Blvd, $4.97
3. Target on Guadalupe St, $5.80
Prices from their sites today, may differ in store.
```

```text
*Weekly Budget*
If you make these every day and shop once a week:
- Tortillas, 2 packs: $3.78
- Salsa, 2 jars: $4.50
- Limes, 7: $2.45
- Eggs, 2 dozen: $5.00
- Black beans, 6 cans: $4.74
- Frozen spinach, 2 bags: $2.50
- Onions, 3 lb bag: $2.49
About $25.46 a week, well under your $5 a meal (about $105 a week). Rice, oil and salt left out, you keep them
stocked.
```

```text
*Nutrition Goal*
Got a calorie or nutrition goal? Like "2000 cal a day" or "high protein". I'll plan your meals toward it.
```

When something is missing, the prompts message looks like this:

```text
Send your ZIP or campus and I'll find the cheapest stores near you.
Send a pic of your pantry or fridge, or just list what you have, and I'll build the meals around it.
```

With a nutrition goal saved, the last message looks like this:

```text
*Nutrition Goal*
Today comes to about 1,750 cal and 65 g protein (est.). Your goal is 2000 cal a day, so add a snack or a bigger
dinner.
```

## When something fails

- The profile script returns an error: follow its exit code in the table above. Never suggest a recipe without
  a readable profile and known allergies.
- Photo too dark or blurry: ask for a clearer photo, or a quick list of what they have.
- No location: send the reply anyway with estimated costs, and ask for a ZIP or campus in the prompts. If they'd
  rather not share it, stop asking and fill *Stores Near You* with general tips (store brands, weekly ads)
  instead of store prices.
- Store sites won't load or show no prices: send the recipes and the list, name the nearest stores, and say
  prices aren't available right now. Retry at most once.
- Nothing fits the budget: say so and offer the closest cheaper version (a smaller batch, swaps, fewer items).
  Never go over the budget without saying so.
- Every option breaks an allergy or diet rule: say none fit and ask what else they have.
- If the student mentions an allergic reaction or trouble breathing, tell them to use their epinephrine
  auto-injector if they have one and call 911 (or the local emergency number) now. Don't troubleshoot.
- Without photos, the web, the browser or a way to run the script (for example outside Cubbie): ask for the
  ingredients, allergies and diet in text at the start, and skip the price check.
