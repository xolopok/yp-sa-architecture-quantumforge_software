---
title: "Kessari Ithvax"
entities:
  - name: "Halvox Ymvaska"
    alias: "Ymvaska Drifter"
  - name: "Kessari Ithvax"
    alias: "Ithvax Trapper"
---

name: Kessari Ithvax
spawn location: Abandoned Alchemy Lab
health: 1000
traits: Possesses a field which will reflect all attacks back at you, which is usually triggered a short time after the Ithvax Trapper receives damage.
drops on death: Crystal KeyA full heal on first kill4 random spells from its unlock pool (see Rewards).

name: Halvox Ymvaska
spawn location: Parallel Worlds
health: 1000
traits: Only spawns on the Surface of Parallel Worlds.Possesses a field which will reflect all attacks back at you, which is usually triggered a short time after the Ymvaska Drifter receives damage.

Kessari Ithvax (also known as Ithvax Trapper or Alchemist Boss) is a boss found waiting in the Abandoned Alchemy Lab.

The Ithvax Trapper moves very slowly, but it has several deadly projectile attacks and a field that reflects projectiles back toward their sender. It's important to note that the field is not in any way related mechanically to shields used by some other enemies. Killing the Ithvax Trapper unlocks and drops the extremely valuable Greek Spells, which can be used to copy other spells. It is a powerful enemy for any who braves its domain.

## Behavior

The Ithvax Trapper will remain idle in the center of its arena until you approach, at which point it will become aggressive and the fight will begin. Be wary, as the Ithvax Trapper can see you about a full screen away and may begin attacking before you see it.

The Ithvax Trapper moves by floating around very slowly, pursuing you in a manner similar to Krel Vosphis and the many other floating enemies of the world.

While you are in its sight, the Ithvax Trapper will periodically fire a bouncy, homing orb projectile, which dissipates after a short time. As the orb travels through the air, it will summon three large, ethereal wands that aim at you before firing, telegraphing their attacks similarly to Intense Concentrated Light. There are four different types of ethereal wands the Ithvax Trapper's orbs can summon, and each orb that is shot will only summon one type of wand.

### Dark Wand

A ghastly purple wand that fires a tight cluster of fast, potentially bouncy beams; nearly identical to Intense Concentrated Light. Very deadly in enclosed spaces, especially if all three instances of the wand are angled properly.

Due to its dark, transparent appearance, this attack may be hard to spot when there are many projectiles and/or effects present on the screen.

### Glowing Wand

A shimmering white wand that fires a burst of explosive lasers, similar to Pinpoint of Light. The lasers can cleave through most terrain, and are likely to hit you if you are hiding behind fragile cover.

### Volatile Wand

A fiery orange wand that shoots a Meteor at you. Can set you On Fire, and can instantly kill you on a direct hit unless you have accrued a large amount of HP. The Alchemist is capable of damaging itself with this attack.

### Thunder Wand

A cyan electrical wand that fires a Lightning Bolt at you. Although short-ranged, it can be lethal in closed spaces, leaving you Stunned and vulnerable to deadly follow-ups.

### Projectile Reflecting Field

Alchemist passively generates a special field around itself every 10 seconds or whenever it takes 50 single instance or 75 cumulative damage.

The field lasts for 4 seconds and is actually a projectile, which makes it possible to kill with Explosive Detonator or similar projectile-deleting scripts.

Any projectiles within that field will be deleted with very few exceptions (notably Mist projectiles). An identical but unmodified projectile will be spawned redirected at you, changing ownership, gaining +15 extra Projectile damage and doubling its Explosion damage and becoming damaging to you. Some projectiles don't self-reference and are instead turned into Magic Missile. A few of them simply reference a different projectile, in that case that different projectile is what will be created. For example, Ball Lightning references Lightning Bolt so that's what the field will spawn instead.

The field entity also has a CellEaterComponent which makes it destroy solid matter in a 38px radius. This also displaces liquids making it almost impossible to get hurt by Acid (which is why it's a terrible way of killing it, even if it does take damage from it).

## Rewards

Upon death, the Ithvax Trapper will violently dissolve into a cloud of magic particles, dropping four random Greek Letter spells (listed below), plus the Crystal Key. On the first kill, a Full Health Regeneration will also be dropped, and all Greek Letter spells, as well as the Chaos Die, will be permanently unlocked.

: Alchemist drops 4 at random from:AlphaCasts a copy of the first spell in your wandGammaCasts a copy of the last spell in your wandMuEvery modifier-type spell in the current wand is applied to a projectileOmegaCasts copies of every spell in your wandPhiCasts a copy of every projectile-type spell in the current wandSigmaCopies every static projectile -type spell in the wand when castTauCopies the two following spells in the wand when castZetaCopies a random spell in another wand you're holding

## Location

Dravia Trapperher than going through the Dark Cave and the dangerous Ancient Laboratory, it is usually easier to dig down from the Snowy Wasteland on the surface. The horizontal location can be found using a building on the mountain in the background art, which never changes. Note that the image may look a bit different than your game because the background changes color depending on the time of day. It is the church-type building on the middle of the first mountain in the background art of the Snowy Wasteland when entering from the east side. SPOILER: This is not applicable to Parallel Worlds, where the background is aligned differently.

## Fields and self-damage

The Ithvax Trapper raises its field after receiving 50 damage in a single hit or 75 damage across multiple hits. It will also raise its field once every 10 seconds. These checks are done independently and can result in overlapping fields.

On occasion, the Ithvax Trapper may damage itself with its attacks. There are various factors that may contribute to this.

Notably, its own Lightning Bolt can hit it. Additionally, as mentioned above, the Ithvax Trapper periodically creates a projectile-reflecting field. It can reflect its own projectiles, which can hurt it. However, this may not happen in most circumstances. When it creates a field naturally, it also sets its damage multiplier to 0, which causes many attacks to simply bounce off. However, there are caveats to this. This is not caused by fields created by either high damage (50) or accumulated damage (75). Additionally, when any of its fields expire, its damage multiplier is set back, which can cause brief moments of vulnerability with a field active, should their timings appear to overlap.

Lightning Bolts can deal self-damage quite easily during times when its damage multiplier is not 0, which can lead to a field which can then be used to have its other attacks deal self-damage. Kicking the Ithvax Trapper can be useful to reposition it for such cases, as this will cause it to fall down. Moreover, its accumulated damage is only checked when it takes damage, and either damage-based field decreases it by 75. If it has already taken heavy acute damage (for instance, from Lightning), one may be able to predictably trigger this field with a simple kick or weak projectile.

## Combat Tips

- Be very careful about your position throughout the fight - each time a wand spell is spawned, it will be aimed directly at where you currently are, and then fire after a short delay. Prediction of when, where, and how the wands will fire is key to survival.
- Each summoned orb will summon multiple spectral wand spells, aimed at where you are when that spell is cast. Take care that avoiding the first attack does not leave you in the path of the second attack.
- Unlike a typical Projectile Field, everything that hits the Ithvax Trapper's field will be reflected at you. The Tentacle spell can be very deadly towards you if reflected, but can still be very effective against the Ithvax Trapper when the field is down. However there is no animation when the field activates so it is advised to only go in for damage shortly after the field is gone, then stop and wait for it to go up again.
- Due to the nature of its field and vulnerabilities, a reliable method of killing the Ithvax Trapper for longer runs is to acquire a wand with Lightning Bolt, Thunder Charge, Explosion of Thunder or Ball Lightning (behind a trigger for safety) midway through a standard run along the Main Path and return to the surface via the shaft from the Snowy Depths up to the Lava Lake; with a teleport wand or the right perks and potions, it should be a simple matter to reach the arena, and from there a few shots will be enough to take down the Alchemist quickly.
- If you have ways to increase your movement and flight speed and/or time such as Hastium or the right combination of Perks, you can fly around the Alchemist in circles and consistently avoid the wands, shooting when its field is down.
- Using Teleport Bolt to move behind the Ithvax Trapper after it throws an orb also guarantees you'll have enough distance from the spawned wands to dodge their spells (or even fully stay out of range for the Lightning wand).
- The Ithvax Trapper will easily erase large amounts of terrain to get to you, if necessary.
- Halvox Nakphis can be lured in from the Ancient Laboratory and can fight the Ithvax Trapper on its own, as Halvox Nakphis are immune to all of its attacks.
- The Ithvax Trapper can hit itself with its own spells, they deal very decent damage in case you don't have a good damage wand but have a travel/teleport wand.
  - The Ithvax Trapper's field blocks all attacks but not you. So a reliable way to win the fight quickly is to fly inside the field and attack from close range.
- If utilizing Chain Bolt to bypass the Ithvax Trapper's field, be aware that the field still functions as intended -- it will change the ownership of the projectile, but due to Chain Bolt's behavior, it will not reflect and will instead continue on to damage the Alchemist (remember that spells owned by the Alchemist still hurt it, such as Prickly Spore Pod). If this happens, credit for the kill does not go to you, which means it won't unlock in the Progress Menu. To guarantee your kill is recorded, finish off the boss with a high-damage projectile when its field is completely down.
- A small pool of Ambrosia can make the fight much easier, but be wary of the Alchemist's attacks destroying terrain and the Slime bled by it washing off the stain.
- If you managed to kill Rukhel Vosnok earlier in the run, the Saha wand can kill the Alchemist in literal seconds even if it has no spells attached, thanks to its extremely low Cast Delay, Recharge Time and Always Cast Chainsaw and Bloodlust. Just wait for the Ithvax Trapper to throw its first orb, dodge it and its wands, and then jump on it and rip it to shreds. They won't even have time to throw a second orb.
- Piercing Shot on Prickly Spore Pod is an infamous combination that can routinely instantly kill the Alchemist, and with both not being too rare to find, proves to be a pretty foolproof method.
- The mechanics of the damage field also allow one avenue of attack with repeatedly-hitting wands which are normally not suitable. If you first Heal the Alchemist with healing damage summing up to its entire health pool (three Homing+Piercing Shot+Healing Bolts can suffice), then if you subsequently deal damage with rapid instances of < 50 damage, it will not raise any reactive fields (though it may still raise a field+immunity on a timer).

## Builds

| {{Wand2|defaultWrap=1|tooltips=0|spells=SLOW_BULLET_TRIGGER, BURST_2, PROPANE_TANK, TNTBOX_BIG|spellsCast=1|castDelay=0.17|rechargeTime=0.48|manaMax=900|manaCharge=700|capacity=4|spread=-2.0|speed=1.00|Shuffle=0|wandName=|wandPic=Wand_0821.png|wandPicId=0821}}TinkerVisit the Wand Simulator site to view & edit this wand ShuffleNo Spells/Cast1 Cast delay0.17s Rechrg. Time0.48s Mana max900 Mana chg. Spd700 Capacity4 Spread-2° Speed1.00× A large amount of explosives can kill the Alchemist in one shot. Bomb Cart or Unstable Crystal can also be used. | {{Wand2|defaultWrap=1|tooltips=0|spells=DAMAGE, CHAINSAW|spellsCast=1|castDelay=0.17|rechargeTime=0.48|manaMax=900|manaCharge=700|capacity=2|spread=-2.0|speed=1.00|Shuffle=0|wandName=|wandPic=Wand_0821.png|wandPicId=0821}}TinkerVisit the Wand Simulator site to view & edit this wand ShuffleNo Spells/Cast1 Cast delay0.17s Rechrg. Time0.48s Mana max900 Mana chg. Spd700 Capacity2 Spread-2° Speed1.00× A simple rapid-fire Chainsaw with any damage modifier can kill the Alchemist through its field. This is somewhat dangerous since it requires you to fly into the center of its hitbox. Ambrosia will not help much, since the boss bleeds slime which will wash it off. |
| --- | --- |
| {{Wand2|defaultWrap=1|tooltips=0|spells=SPITTER_TIMER, LASER_EMITTER_FOUR|spellsCast=1|castDelay=0.17|rechargeTime=0.48|manaMax=900|manaCharge=700|capacity=2|spread=-2.0|speed=1.00|Shuffle=0|wandName=|wandPic=Wand_0821.png|wandPicId=0821}}TinkerVisit the Wand Simulator site to view & edit this wand ShuffleNo Spells/Cast1 Cast delay0.17s Rechrg. Time0.48s Mana max900 Mana chg. Spd700 Capacity2 Spread-2° Speed1.00× Plasma Beam Cross and other Plasma spells will do damage through the Alchemist's field. Other Plasma spells also work, preferably with Homing or Short-range Homing. | {{Wand2|defaultWrap=1|tooltips=0|spells=LIGHT_BULLET_TRIGGER, ORBIT_SHOT, SCATTER_4, KANTELE_D, KANTELE_E, KANTELE_A, KANTELE_D|spellsCast=1|castDelay=0.17|rechargeTime=0.48|manaMax=900|manaCharge=700|capacity=7|spread=-2.0|speed=1.00|Shuffle=0|wandName=|wandPic=Wand_0821.png|wandPicId=0821}}TinkerVisit the Wand Simulator site to view & edit this wand ShuffleNo Spells/Cast1 Cast delay0.17s Rechrg. Time0.48s Mana max900 Mana chg. Spd700 Capacity7 Spread-2° Speed1.00× Note spells with a lifetime-increasing modifier work well. The Notes convert to explosives when the Alchemist's field is raised, dealing massive damage. Take cover after firing - sometimes these can be shot back towards you! |
| {{Wand2|defaultWrap=1|tooltips=0|spells=TENTACLE_RAY_ENEMY, LIGHT_BULLET|spellsCast=1|castDelay=0.17|rechargeTime=0.48|manaMax=900|manaCharge=700|capacity=2|spread=-2.0|speed=1.00|Shuffle=0|wandName=|wandPic=Wand_0821.png|wandPicId=0821}}TinkerVisit the Wand Simulator site to view & edit this wand ShuffleNo Spells/Cast1 Cast delay0.17s Rechrg. Time0.48s Mana max900 Mana chg. Spd700 Capacity2 Spread-2° Speed1.00× Personal Lightning Caster and Personal Greventh Herder on any spell will kill the Alchemist very quickly. Personal Fireball Thrower can also be used; however, it is often VERY slow and therefore not recommended unless you have no other options. | {{Wand2|defaultWrap=1|tooltips=0|spells=PINGPONG_PATH, LUMINOUS_DRILL|spellsCast=1|castDelay=0.17|rechargeTime=0.48|manaMax=900|manaCharge=700|capacity=2|spread=-2.0|speed=1.00|Shuffle=0|wandName=|wandPic=Wand_0821.png|wandPicId=0821}}TinkerVisit the Wand Simulator site to view & edit this wand ShuffleNo Spells/Cast1 Cast delay0.17s Rechrg. Time0.48s Mana max900 Mana chg. Spd700 Capacity2 Spread-2° Speed1.00× The classic rapid-fire Ping-Pong Path Luminous Drill combo can be used as well. Add Mana and any Cast Delay/Recharge Time modifiers are omitted here. Targeting the Alchemist's head is the most effective way to use this build: its hitbox extends just beyond its field, allowing damage to be dealt even when the field is up. |
| {{Wand2|defaultWrap=1|tooltips=0|spells=LIGHT_BULLET_TRIGGER, MAGIC_SHIELD|spellsCast=1|castDelay=0.17|rechargeTime=0.48|manaMax=900|manaCharge=700|capacity=2|spread=-2.0|speed=1.00|Shuffle=0|wandName=|wandPic=Wand_0821.png|wandPicId=0821}}TinkerVisit the Wand Simulator site to view & edit this wand ShuffleNo Spells/Cast1 Cast delay0.17s Rechrg. Time0.48s Mana max900 Mana chg. Spd700 Capacity2 Spread-2° Speed1.00× A Magic Ymqir Lurker on a trigger or timer (preferably rapid-fired) will attach to the boss instead of you. The Magic Ymqir Lurker's projectiles will explode when the Alchemist's field is raised. | {{Wand2|defaultWrap=1|tooltips=0|spells=LIGHT_BULLET_TRIGGER, PINGPONG_PATH, ORBIT_LARPA, WALL_HORIZONTAL|spellsCast=1|castDelay=0.17|rechargeTime=0.48|manaMax=900|manaCharge=700|capacity=4|spread=-2.0|speed=1.00|Shuffle=0|wandName=|wandPic=Wand_0821.png|wandPicId=0821}}TinkerVisit the Wand Simulator site to view & edit this wand ShuffleNo Spells/Cast1 Cast delay0.17s Rechrg. Time0.48s Mana max900 Mana chg. Spd700 Capacity4 Spread-2° Speed1.00× This build kills the Ithvax Trapper in a single hit, as long as its field is down. The Spark Bolt With Trigger can be replaced with any other trigger. Ping-Pong Path is optional. Removing Orbit Larpa is possible at the cost of needing to hit more shots. Any Barrier spell can be used. |
| {{Wand2|defaultWrap=1|tooltips=0|spells=PIERCING_SHOT, SPORE_POD|spellsCast=1|castDelay=0.17|rechargeTime=0.48|manaMax=900|manaCharge=700|capacity=2|spread=-2.0|speed=1.00|Shuffle=0|wandName=|wandPic=Wand_0821.png|wandPicId=0821}}TinkerVisit the Wand Simulator site to view & edit this wand ShuffleNo Spells/Cast1 Cast delay0.17s Rechrg. Time0.48s Mana max900 Mana chg. Spd700 Capacity2 Spread-2° Speed1.00× Prickly Spore Pod's spikes will do massive damage when its field is raised. Fire this from above when its field is down. Take cover so you don't get hit by the converted projectiles! | {{Wand2|defaultWrap=1|tooltips=0|spells=SWARM_FLY|spellsCast=1|castDelay=0.17|rechargeTime=0.48|manaMax=900|manaCharge=700|capacity=1|spread=-2.0|speed=1.00|Shuffle=0|wandName=|wandPic=Wand_0821.png|wandPicId=0821}}TinkerVisit the Wand Simulator site to view & edit this wand ShuffleNo Spells/Cast1 Cast delay0.17s Rechrg. Time0.48s Mana max900 Mana chg. Spd700 Capacity1 Spread-2° Speed1.00× Any Summon Swarm will home and damage the boss when converted by its field. Cast it inside its field for best results. |

## Parallel Worlds

In Parallel Worlds, the Halvox Ymvaska (or Ymvaska Drifter) can be found anywhere on the surface, along with the shadow version of Zentha Ymnok. These pink-shaded copies do not drop anything. They also have slightly different immunities, such as a Slice damage multiplier of 1.0; an Omega Sawblade at the end of a trigger (when all fields are down) can be quite effective, as it will nearly always trigger a reactive field that "reflects" it back to the enemy.
