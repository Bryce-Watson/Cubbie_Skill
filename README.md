# Pantry to Plate

A [Cubbie](https://cubbie.ai/) Skill that turns a pantry photo or ingredient list into cheap breakfast, lunch
and dinner recipes. It respects the student's allergies, diet and budget, finds the nearby stores with the best
prices for anything missing, and works out what the groceries would cost each week.

## What it does

Send Cubbie a photo of your pantry or fridge, or a list of what you have, and it replies with five short
messages:

1. **Recipes**: breakfast, lunch and dinner, each with its ingredients (what you have and what to buy) and a
   cost estimate.
2. **Stores Near You**: up to three nearby stores with the price of what you still need, cheapest first.
3. **Prompts**: asks for anything it's missing, such as your location or a pantry photo.
4. **Weekly Budget**: what buying the same items every week would cost, compared with your budget.
5. **Nutrition Goal**: asks for your calorie or nutrition goal, or shows how the day's meals compare to it.

Your allergies, diet, budget, kitchen setup, location and nutrition goal are saved in a small profile file, so
after the first time you only need to send a photo. Allergies are always asked about first, and no recipe is
suggested until they are known.

## What's in this repo

```text
pantry-to-plate/pantry-to-plate/
├── SKILL.md                  # instructions Cubbie follows
├── scripts/food_profile.py   # saves the food profile (Python 3.8+, standard library only)
└── assets/sample_profile.json  # sample profile for testing
```

## Add the Skill to Cubbie

1. Clone this repo:

   ```sh
   git clone https://github.com/Bryce-Watson/Cubbie_Skill.git
   ```

2. Open [Cubbie](https://cubbie.ai/) and add the `pantry-to-plate/pantry-to-plate` folder as a Skill. If Cubbie
   asks for a zip file, make one from that folder:

   ```sh
   cd Cubbie_Skill/pantry-to-plate
   zip -r pantry-to-plate.zip pantry-to-plate
   ```

The Skill needs no sign-in, API key or packages.

## Test the profile script on your computer

You can check the script without Cubbie. Run these from `pantry-to-plate/pantry-to-plate`.

Use the bundled sample profile. This reads `assets/sample_profile.json` and saves nothing:

```sh
python3 scripts/food_profile.py --sample show
```

To try saving changes without touching your real profile, point `HOME` at a temporary folder first:

```sh
export HOME=$(mktemp -d)

python3 scripts/food_profile.py show
python3 scripts/food_profile.py add --allergy 'peanuts:severe' --diet 'vegetarian'
python3 scripts/food_profile.py set --budget '$5 a meal' --location '78705' --kitchen 'microwave' --kitchen 'stove'
python3 scripts/food_profile.py set --nutrition-goal '2000 cal a day, high protein'
python3 scripts/food_profile.py show
```

What to check:

- `show` on an empty profile lists `allergies` first under `missing`, and `safety_line` is `null`.
- After adding the allergy, `safety_line` reads `Checked against your profile: no peanuts (severe), vegetarian.`
- Every change prints a `confirmation` line that ends with the allergies on file.
- These are refused with the exit code shown (run `echo $?` after each one):

  | Command | Expected exit code |
  | --- | --- |
  | `python3 scripts/food_profile.py set --location '123 Main St'` | 2 (street address refused) |
  | `python3 scripts/food_profile.py remove --allergy 'peanuts'` | 3 (needs the student's yes) |
  | `python3 scripts/food_profile.py remove --dislike 'olives'` | 4 (not in the profile) |

When you're done, close the terminal or run `unset HOME` and open a new one so `HOME` goes back to normal.

## Test the Skill in Cubbie

After adding the Skill, send Cubbie these messages in order and check the replies.

| Send | What should happen |
| --- | --- |
| "what can I make for cheap this week?" | Cubbie asks about food allergies before anything else. |
| "allergic to peanuts, it's severe" | Cubbie confirms the allergy, then asks for your budget, diet, kitchen and ZIP in one message. |
| "$5 a meal, vegetarian, microwave + stove, 78705" | Cubbie confirms what it saved. |
| A photo of your pantry or fridge | The five-part reply: Recipes, Stores Near You, Weekly Budget and Nutrition Goal (the prompts message is left out because nothing is missing). Each recipe starts from the line `Checked against your profile: no peanuts (severe), vegetarian.` |
| "dinner" | The full dinner recipe with amounts and steps, starting with the safety line again. |
| "2000 cal a day" | Cubbie saves the goal. On the next recipe reply, the Nutrition Goal section shows how the day compares. |
| "make me a peanut stir-fry" | Cubbie points out the peanut allergy and asks whether the profile is out of date before suggesting anything. |

More things to try:

- Skip the location (or start a new profile without one) and check that the prompts message asks for your ZIP or
  campus.
- Send a text list instead of a photo: "rice, eggs, frozen veggies".
- Ask "what do you remember about my food?" to see the saved profile.
- Prices are marked "est." unless Cubbie found them on a store's site, and the Stores Near You section says where
  they came from.

## License

[MIT](LICENSE.md) © 2026 Ahmed Shaheen and Bryce Watson
