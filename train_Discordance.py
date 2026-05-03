'''
Description: Trains Discordance on nearby enemies until skill cap is reached.
    Automatically selects all enemies in range and keeps attempting to discord
    each one until they are all successfully discorded, then picks fresh targets.

    NOTE: In a future iteration the script will also detect when discorded mobs
    recover and re-apply discord automatically.
'''

discordTimerMilliseconds  = 10200   # cooldown between discord attempts (ms)
searchRange               = 8       # tile radius to scan for enemies
discordEffectDurationMs   = 30000   # how long to stay hidden after discording all targets (ms);
                                    # adjust to match the discord duration on your shard
MIN_HIDING_SKILL          = 30.0    # minimum Hiding skill to attempt UseSkill('Hiding')
MIN_MAGERY_SKILL          = 52.0    # minimum Magery for Invisibility (6th circle)
debugMode                 = True    # set to False once outcome detection is working;
                                    # when True, unmatched journal lines are printed to chat

import config
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glossary.items.instruments import FindInstrument
from glossary.colors import colors
from glossary.enemies import GetEnemies

# ── Helpers ───────────────────────────────────────────────────────────────────

def PickInstrument():
    '''Returns an instrument from the backpack, or None.'''
    return FindInstrument( Player.Backpack )


def IsDiscordedByProps( mobile ):
    '''
    Checks the mobile's tooltip properties for a discord indicator.
    Returns True if any property line contains a discord-related keyword.
    This is the most reliable way to detect discord status without relying
    solely on journal messages.
    '''
    Mobiles.WaitForProps( mobile.Serial, 1000 )
    props = Mobiles.GetPropStringList( mobile.Serial )
    if props is None:
        return False
    for line in props:
        lower = line.lower()
        if 'discord' in lower or 'discorded' in lower:
            return True
    return False


def UseInstrumentTarget( instrument, target ):
    '''
    Fires the Discordance skill. Handles the "What instrument shall you play?"
    selection prompt if it appears.  Returns the instrument still in use, or
    None if no instrument is available.
    '''
    Journal.Clear()
    Player.UseSkill( 'Discordance' )
    Misc.Pause( config.journalEntryDelayMilliseconds )

    if Journal.Search( 'What instrument shall you play?' ):
        instrument = PickInstrument()
        if instrument is None:
            Target.Cancel()
            Misc.SendMessage( 'Ran out of instruments!', colors[ 'red' ] )
            return None
        Target.WaitForTarget( 2000, True )
        Target.TargetExecute( instrument.Serial )

    Target.WaitForTarget( 2000, True )
    Target.TargetExecute( target )
    return instrument


# ── Concealment helper ───────────────────────────────────────────────────────

def HidePlayer():
    '''
    Tries to conceal the player after all targets are discorded.
    Priority:
      1. Hiding skill (if >= MIN_HIDING_SKILL) — UseSkill and confirm via journal.
      2. Invisibility spell (if Magery >= MIN_MAGERY_SKILL and sufficient mana).
    Returns True if concealment was confirmed, False otherwise.
    '''
    hidingSkill = Player.GetSkillValue( 'Hiding' )
    magerySkill = Player.GetSkillValue( 'Magery' )

    if hidingSkill >= MIN_HIDING_SKILL:
        Journal.Clear()
        Player.UseSkill( 'Hiding' )
        Timer.Create( 'hide_confirm', 3000 )
        while Timer.Check( 'hide_confirm' ):
            if Journal.Search( 'You are now hidden' ):
                Misc.SendMessage( 'Hidden successfully.', colors[ 'cyan' ] )
                return True
            if Journal.Search( "You can't seem to hide" ) or Journal.Search( 'fail' ):
                break
            Misc.Pause( 100 )
        Misc.SendMessage( 'Could not hide — continuing visible.', colors[ 'yellow' ] )
        return False

    elif magerySkill >= MIN_MAGERY_SKILL and Player.Mana >= 20:
        Spells.CastMagery( 'Invisibility' )
        Target.WaitForTarget( 4000, True )
        Target.TargetExecute( Player.Serial )
        Misc.Pause( 2000 )
        if Player.BuffsExist( 'Invisibility' ):
            Misc.SendMessage( 'Invisible — waiting for discord to wear off.', colors[ 'cyan' ] )
            return True
        Misc.SendMessage( 'Invisibility did not confirm — continuing visible.', colors[ 'yellow' ] )
        return False

    else:
        Misc.SendMessage(
            'No concealment available (need Hiding >= %.0f or Magery >= %.0f).' % ( MIN_HIDING_SKILL, MIN_MAGERY_SKILL ),
            colors[ 'yellow' ]
        )
        return False


# ── Main training loop ────────────────────────────────────────────────────────

def TrainDiscordance():
    '''
    Cycles through all enemies in range, attempting to discord each one.
    Keeps retrying any mob that resists until it is successfully discorded,
    then moves on to the next.  Stops when the skill cap is reached.
    '''
    instrument = PickInstrument()
    if instrument is None:
        Misc.SendMessage( 'No instrument found in your backpack!', colors[ 'red' ] )
        return

    Misc.SendMessage( 'Starting Discordance training — skill: %.1f' % Player.GetSkillValue( 'Discordance' ), colors[ 'cyan' ] )
    Timer.Create( 'discordTimer', 1 )   # expire immediately so first use fires at once

    skillCap       = Player.GetSkillCap( 'Discordance' )
    discordedSerials = set()   # serials successfully discorded this session

    while instrument is not None and Player.GetSkillValue( 'Discordance' ) < skillCap and not Player.IsGhost:

        enemies = GetEnemies( Mobiles, 0, searchRange )

        # Prune serials of mobs that have left range or died
        discordedSerials = { s for s in discordedSerials if Mobiles.FindBySerial( s ) is not None }

        undiscorded = [ e for e in enemies if e.Serial not in discordedSerials ]

        if len( undiscorded ) == 0:
            if len( enemies ) == 0:
                Misc.SendMessage( 'No enemies in range — waiting...', colors[ 'yellow' ] )
                Misc.Pause( 1000 )
            else:
                Misc.SendMessage(
                    'All %d enemies discorded — concealing for up to %ds.' % ( len( enemies ), discordEffectDurationMs // 1000 ),
                    colors[ 'green' ]
                )
                HidePlayer()
                # Wait for the discord effect to wear off, breaking early if any
                # target recovers or a new enemy enters range.
                Timer.Create( 'discordEffectTimer', discordEffectDurationMs )
                while Timer.Check( 'discordEffectTimer' ) and not Player.IsGhost:
                    curEnemies = GetEnemies( Mobiles, 0, searchRange )
                    discordedSerials = { s for s in discordedSerials if Mobiles.FindBySerial( s ) is not None }
                    if any( e.Serial not in discordedSerials for e in curEnemies ):
                        Misc.SendMessage( 'Target recovered or new enemy — re-engaging.', colors[ 'cyan' ] )
                        break
                    Misc.Pause( 1000 )
                # Clear so all enemies are re-discorded on the next sweep
                discordedSerials.clear()
            continue

        # Attempt to discord every un-discorded enemy in range before looping back
        for enemy in undiscorded:
            if Player.IsGhost:
                break
            if Player.GetSkillValue( 'Discordance' ) >= skillCap:
                break

            fresh = Mobiles.FindBySerial( enemy.Serial )
            if fresh is None:
                continue   # mob died or moved out of range

            # Keep trying this mob until the discord lands or it disappears
            discorded = False
            attempts  = 0
            while not discorded and not Player.IsGhost:
                fresh = Mobiles.FindBySerial( enemy.Serial )
                if fresh is None:
                    break   # mob is gone — move to next target

                # Check props first — if the mob is already discorded don't
                # waste a skill use or instrument charge.
                if IsDiscordedByProps( fresh ):
                    discorded = True
                    discordedSerials.add( fresh.Serial )
                    Misc.SendMessage( 'Already discorded: %s — skipping.' % fresh.Name, colors[ 'green' ] )
                    break

                # Respect the skill use timer
                while Timer.Check( 'discordTimer' ) and not Player.IsGhost:
                    Misc.Pause( 100 )

                Mobiles.Message( fresh, colors[ 'cyan' ], 'Discording...' )
                instrument = UseInstrumentTarget( instrument, fresh )
                if instrument is None:
                    return   # no instruments left — abort entirely

                # Wait for a System-type outcome message (up to 4 s).
                # Discord outcomes are grey System messages in the journal.
                Timer.Create( 'discord_outcome', 4000 )
                while Timer.Check( 'discord_outcome' ):
                    if ( Journal.SearchByType( 'You play', 'System' ) or
                         Journal.SearchByType( 'falls under', 'System' ) or
                         Journal.SearchByType( 'confused', 'System' ) or
                         Journal.SearchByType( 'affected', 'System' ) or
                         Journal.SearchByType( 'already', 'System' ) or
                         Journal.SearchByType( 'discord', 'System' ) or
                         Journal.SearchByType( 'fail', 'System' ) ):
                        break
                    Misc.Pause( 100 )

                Timer.Create( 'discordTimer', discordTimerMilliseconds )

                failed = ( Journal.SearchByType( 'fail', 'System' ) or
                           Journal.SearchByType( 'You play but', 'System' ) or
                           Journal.SearchByType( 'not affected', 'System' ) or
                           Journal.SearchByType( 'no effect', 'System' ) )

                alreadyDiscorded = Journal.SearchByType( 'already in discord', 'System' )

                succeeded = ( alreadyDiscorded or
                              ( not failed and (
                                Journal.SearchByType( 'falls under', 'System' ) or
                                Journal.SearchByType( 'loses its concentration', 'System' ) or
                                Journal.SearchByType( 'affected by', 'System' ) or
                                Journal.SearchByType( 'confused', 'System' ) or
                                Journal.SearchByType( 'disrupted', 'System' ) or
                                Journal.SearchByType( 'You play your', 'System' ) ) ) )

                # Also confirm via props if journal was inconclusive
                if not succeeded and not failed:
                    succeeded = IsDiscordedByProps( fresh )

                if succeeded:
                    discorded = True
                    discordedSerials.add( fresh.Serial )
                    Misc.SendMessage( 'Discorded: %s' % fresh.Name, colors[ 'green' ] )
                else:
                    attempts += 1
                    if debugMode and not failed:
                        hits = []
                        for probe in ( 'You play', 'fails', 'falls', 'confused',
                                       'disrupted', 'affected', 'concentration',
                                       'effect', 'music', 'discord', 'already' ):
                            if Journal.SearchByType( probe, 'System' ):
                                hits.append( probe )
                        Misc.SendMessage(
                            '[DEBUG] No outcome matched. System keywords found: %s' % ( hits if hits else 'none' ),
                            colors[ 'yellow' ]
                        )
                    Misc.SendMessage( 'Attempt %d on %s failed — retrying.' % ( attempts, fresh.Name ), colors[ 'yellow' ] )

        Misc.Pause( 200 )   # short breath between full sweeps

    if Player.GetSkillValue( 'Discordance' ) >= skillCap:
        Misc.SendMessage( 'Discordance is at cap (%.1f)! Done.' % skillCap, colors[ 'green' ] )
    elif instrument is None:
        Misc.SendMessage( 'No instruments remaining — stopping.', colors[ 'red' ] )


# ── Entry point ───────────────────────────────────────────────────────────────

TrainDiscordance()
