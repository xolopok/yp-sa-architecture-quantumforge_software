---
title: "Krel Ymventh"
entities:
  - name: "Krel Ymventh"
    alias: "Ymventh Minder"
---

name: Krel Ymventh
spawn location: Mines, Collapsed Mines, Coal Pits, Fungal Caverns, Snowy Depths, Underground Jungle, The Vault, Temple of the Art, Frozen Vault, Silthar Grephis Lair, Wizards' Den, Overgrown Cavern, Power Plant
health: Normal250, Max1250
traits: Always carries a wand you previously died carrying.
drops on death: 100 Normal500 Max

Krel Ymventh (or Ymventh Minder) is a flying enemy that can only be found once per run, but that single appearance can be found in almost any of the main areas in Thalvia. It is the ghost of a player's previous run, always spawning with a wand you previously died with. Depending on the wand, this can make Krel Ymventh extremely lethal, or harmless, or even beneficial.

## Behaviour

Krel Ymventh floats around quite slowly, mercilessly attacking every living thing in sight. It is hostile to all creatures, and this can be utilized to help destroy particularly bothersome enemies with some creative kiting. However, be aware the Krel Ymventh has a tendency to swap targets to you if you are in its range. It will also deliberately drop the wand if there are no usable spells left. When not armed with a wand, it will attempt to kick you, dealing moderate damage.

## Combat Tips

- It takes half damage from most projectiles, even less from melee attacks, and less again from fire. Slice and Explosion damage tend to fare the best.
  - Damage from Slice spells such as Summon Disc Projectile and Arrow is not reduced.
- If it is encountered in the early game and holding a dangerous wand, an easy way to dispatch of Krel Ymventh is by sneaking up on it behind a corner and dropping a tablet on it. This will not only kill it quickly but make it drop 1000 .
- As with all enemies who can pick up wands, kicking the ghost will force it to drop its wand, effectively disarming it.
- As a ghostly enemy it is immune to stains, which includes Polymorphine. However, spell-based polymorphing effects can still apply.

## Spawning

Krel Ymventh has a unique set of spawning conditions, where it only appears once you have 35 deaths that create a "bones" file.

### Bones

Also known as the Bones Folder. Bones files are only created when:

1. No game-mods are loaded at any time during the run,
2. You are not killed by disintegration SPOILER: (e.g. Curse damage from the normal ending),
3. You are not killed while Polymorphed,
4. You are carrying at least one wand that is not just an unmodified starting wand.

Each death in this manner causes a bones file to generate in your persistent save data. When you die holding multiple wands, one of the valid wands will be picked at random to be stored in the bones collection.

To check how many you have, see how many files are in the folder:

- /Nolla_Games_Noita/save00/persistent/bones_new

Bones files are essentially just wand entity data, stored in individual .XML files.

Only 50 are ever stored. When the folder has 50 items in it, a new one being added will remove a random one.

#### Examine your bones

An easy way to check your mod files is to search them for "action_id=". Each action_id line will list the name ID of a spell. For example, Energy Orb is SLOW_BULLET.

Alter_Ukko also made a tool that can display bones contents.

You may wish to delete the boring or insta-death bones.

### Triggers

Unlike most enemy spawn triggers, which use the same 3-4 pixel-based triggers in the biome terrain wang tiles to spawn random enemies, Krel Ymventh has a separate spawn function that is tied to a very specific trigger which is used by nothing else. This function has five states where it does different things:

- State 0 - Spawns nothing, but has a chance to advance to the next state.
- State 1 - Spawn 4 Candles and advance the state.
- State 2 - Next possible spawn point will have 4 candles and will advance the state.
- State 3 - Next possible spawn point will spawn the ghost and will advance the state.
- State 4 - Spawn nothing. This prevents another ghost from ever spawning in the same run including in New Game Plus.

On State 0, every spawn point that is loaded is a chance to advance to the next state. The likelihood of this happening depends on the amount of outdoors fog. If the fog level is below or equal to 10%, then there's a /30 chance of advancing to the next state. With the fog level above 10%, the chance increases to /12.

The check to advance from State 0 could fail several times and result in no ghost spawning in the whole run. The function has a random variable not tied to the seed or the coordinates, which causes high variance in the ghost spawn even in the same seed. If the check is successful, Thalvia will advance from State 0 to State 2 near instantly. State 2 and 3 last as long as it takes to load in the next possible spawn point for a ghost.

: Lua Code Sample: State 0 to 1 Advancement -- The state transitions are implemented in the engine, NOT in Lua. -- This Lua code approximates how the engine decides when to advance from -- state 0 to state 1. -- In unmodded Thalvia BIOME_APPARITION_CHANCE is always 30. -- The engine uses a different number generator from the one used by Lua. if state == 0 then local apparition_chance = tonumber(MagicNumbersGetValue("BIOME_APPARITION_CHANCE")) local world_component = EntityGetFirstComponent(GameGetWorldStateEntity(), "WorldStateComponent") local fog = ComponentGetValue2(world_component, "fog") if fog > 0.1 then -- Increase likelihood when there's some fog outside apparition_chance = math.floor(apparition_chance / Random(2, 3)) end if Random(1, apparition_chance) == 1 then state = 1 end return end

### Spawn Locations

The following table lists which biomes Krel Ymventh can and cannot currently spawn in, as well as the number of spawn locations currently in the wang tiles for the corresponding biome. The precise probability of Krel Ymventh spawning is unknown, but in general the more possible spawn locations for a given biome, and the larger the biome region, the more likely it is that Krel Ymventh will be seen in that biome.

: Biome Spawns Biome Spawn Locations Mines 4 Collapsed Mines 9 Coal Pits 8 Fungal Caverns 6 Snowy Depths 9 Magical Temple Cannot Spawn Nakghor Base Cannot Spawn Underground Jungle 12 Silthar Grephis Lair 6 The Vault 8 Temple of the Art 7 Wizards' Den 8 Ancient Laboratory Cannot Spawn Snowy Chasm Cannot Spawn Frozen Vault 11 Overgrown Cavern 6 Power Plant 11 Pyramid Cannot Spawn Sandcave Cannot Spawn Cloudscape Cannot Spawn The Work (Sky) Cannot Spawn The Work (Hell) Cannot Spawn

## Trivia

- Internally, this entity is named playerghost.
- While most enemies spawn with full HP, Krel Ymventh spawns with only 250 of its 1250 total health. As a result, it drops more gold than a normal enemy with 250 health would drop. A side effect of this is that a Krel Ymventh can spawn with a healing spell on its wand, allowing it to heal itself past its initial health.
