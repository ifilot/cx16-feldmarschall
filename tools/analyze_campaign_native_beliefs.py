"""Native belief-to-objective mechanism on frozen historical public roots.

Every policy receives its own setup and public events only. Each policy acts on
all of its forced historical turns, so persistent goals reflect its own earlier
belief decisions. This measures changed behavior, never playing strength.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import tempfile
import time
import zipfile

from ai_registry import ROOT, get_policy
from feldmarschall import Engine, parse_square
from test_information_parent_parity import public_events
from tournament_store import Tournament, replay


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def move_from_protocol(text):
    return None if text == 'none' else tuple(map(parse_square, text.split()))


def run():
    from campaign_native_beliefs import NativeBeliefBot
    folder = ROOT/'docs/ai-honest-campaign-2026-10-15/research/horizon'
    destination = folder/'native-belief-objectives-mechanism.json'
    if destination.exists():
        raise ValueError('preserve completed historical evidence')
    root_source = folder/'quiescence-mechanism.json'
    historical = json.loads(root_source.read_text())
    source = ROOT/historical['source']
    if historical['source_sha256'] != digest(source):
        raise ValueError('historical tournament hash mismatch')
    selections = {}
    for row in historical['roots']:
        selections.setdefault((row['game'], row['army']), {})[row['ply']] = row
    model = ROOT/'ai/models/joint-flag-bomb-beliefs-v1.json'
    policy = get_policy('teacher-context-v1-normal')
    roots, timed_turns = [], Counter()
    all_turn_seconds = Counter()
    with tempfile.TemporaryDirectory(prefix='feld-native-belief-mechanism-') as temporary:
        temporary = Path(temporary)
        with zipfile.ZipFile(ROOT/policy['archive']) as archive:
            archive.extractall(temporary/'source')
        # Hold every other source to the frozen parent. Only the guarded prior
        # API and protocol integration come from current research sources.
        # ai_mission adds only a test accessor needed by the current observer.
        changed_sources = ('src/native/engine.c', 'src/core/ai.c', 'src/core/ai.h',
                           'src/core/ai_mission.c', 'src/core/ai_mission.h')
        for name in changed_sources:
            (temporary/'source'/name).write_bytes((ROOT/name).read_bytes())
        programs = {}
        for name, extra in (('native', []), ('belief', ['AI_BELIEF_PRIORS'])):
            program = temporary/name
            command = ['gcc', '-O2', '-std=c99', '-Wno-unknown-pragmas', '-Wno-format-overflow',
                       '-Isrc/core', '-o', str(program),
                       *['-D'+define for define in policy['defines']+extra], *policy['sources']]
            subprocess.run(command, cwd=temporary/'source', check=True, capture_output=True)
            programs[name] = program
        base = Engine(shlex.quote(str(programs['native'])))
        bots = {mode: NativeBeliefBot(programs['belief'], model, mode=mode)
                for mode in ('counts', 'joint')}
        try:
            with Tournament(source) as tournament:
                for (game_id, army), targets in sorted(selections.items()):
                    game = tournament.game(game_id)
                    states, _ = replay(game)
                    events = public_events(game, states)
                    seed = game['seed']*2+army+1
                    for command in ('new '+('red', 'blue')[army], 'rules 0', 'difficulty normal',
                                    'seed '+str(seed), 'setup '+game[('red_setup', 'blue_setup')[army]]):
                        base.send(command)
                        for bot in bots.values():
                            bot.observe(command.split())
                    for ply, event in enumerate(events[:max(targets)+1]):
                        if ply % 2 == army:
                            is_target = ply in targets
                            if is_target:
                                public = base.ask('public', 'public')
                                assert hashlib.sha256(public.encode()).hexdigest() == targets[ply]['public_sha256']
                                assert all(bot.observer.ask('public', 'public') == public for bot in bots.values())
                                prior_states = {'native': bytes.fromhex(base.ask('strategy', 'strategy'))}
                                prior_states.update({mode: bytes.fromhex(bot.observer.ask('strategy', 'strategy'))
                                                     for mode, bot in bots.items()})
                            selected, seconds, reports = {}, {}, {}
                            order = ['native', 'counts', 'joint']
                            rotation = sum(timed_turns.values())//3 % 3
                            for mode in order[rotation:]+order[:rotation]:
                                started = time.perf_counter()
                                selected[mode] = move_from_protocol(base.ask('go', 'move')) if mode == 'native' else bots[mode].choose()
                                seconds[mode] = time.perf_counter()-started
                                timed_turns[mode] += 1
                                all_turn_seconds[mode] += seconds[mode]
                                if mode != 'native':
                                    reports[mode] = bots[mode].last_report
                            if is_target:
                                after = {'native': bytes.fromhex(base.ask('strategy', 'strategy'))}
                                after.update({mode: bytes.fromhex(bot.observer.ask('strategy', 'strategy'))
                                              for mode, bot in bots.items()})
                                # Goal arrays are the first 200 bytes in all variants.
                                # Priors append 401 bytes; historical memory offsets stay fixed.
                                goal_differences = {mode: sum(a != b for a, b in zip(after['native'][:200], after[mode][:200]))
                                                    for mode in bots}
                                public_after = base.ask('public', 'public')
                                assert public_after == public
                                assert all(bot.observer.ask('public', 'public') == public for bot in bots.values())
                                roots.append(dict(game=game_id, army=army, family=game['family'], ply=ply,
                                                  public_sha256=targets[ply]['public_sha256'], selected=selected,
                                                  seconds=seconds, reports=reports,
                                                  persistent_goal_entries_different=goal_differences,
                                                  prior_native_memory_sha256={mode: hashlib.sha256(value[:len(prior_states['native'])]).hexdigest()
                                                                              for mode, value in prior_states.items()}))
                                print('Historical native-belief root', len(roots), '/ 140', flush=True)
                            played = 'played '+' '.join(event.split()[1:3])
                            base.ask(played, 'playedok')
                            for bot in bots.values():
                                bot.observe(played.split())
                        base.send(event)
                        for bot in bots.values():
                            bot.observe(event.split())
        finally:
            base.close()
            for bot in bots.values():
                bot.close()
        runtime_hashes = {name: digest(program) for name, program in programs.items()}
    summary = dict(roots=len(roots), orientations=dict(Counter(row['army'] for row in roots)),
                   families=dict(Counter(row['family'] for row in roots)),
                   decisions_changed_from_native={mode: sum(row['selected'][mode] != row['selected']['native'] for row in roots)
                                                  for mode in ('counts', 'joint')},
                   count_joint_decisions_different=sum(row['selected']['counts'] != row['selected']['joint'] for row in roots),
                   roots_with_changed_persistent_goals={mode: sum(row['persistent_goal_entries_different'][mode] > 0 for row in roots)
                                                        for mode in ('counts', 'joint')},
                   root_wall_seconds={mode: sum(row['seconds'][mode] for row in roots) for mode in ('native', 'counts', 'joint')},
                   all_forced_own_turns=dict(timed_turns), all_forced_turn_wall_seconds=dict(all_turn_seconds))
    result = dict(schema='historical-native-belief-objectives-v1', strength_evidence=False,
                  source=str(source.relative_to(ROOT)), source_sha256=digest(source),
                  roots_sha256=digest(root_source), model_sha256=digest(model),
                  source_sha256_overlays={name: digest(ROOT/name) for name in changed_sources},
                  runtime_sha256=runtime_hashes,
                  public_input='Own setup, legal public movements/combat, remaining public inventory; no enemy setup or truth.',
                  context='Each mode chooses at every forced historical own turn; persistent native goals may diverge. Actual historical moves are then confirmed identically.',
                  caveat='Decision changes and timing describe mechanism only. No outcome labels select roots or parameters.',
                  summary=summary, roots=roots)
    destination.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(summary, indent=2), flush=True)
    return result


if __name__ == '__main__':
    run()
