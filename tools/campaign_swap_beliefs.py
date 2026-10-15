"""Equal-weight independent rank-swap Metropolis chains for learned beliefs.

Target: product of the frozen model's per-piece likelihoods, conditioned on
the exact remaining rank counts and public masks. Symmetric lazy swaps have
the target as an invariant distribution. Finite fixed burn-in is APPROXIMATE;
unit importance weights do not establish convergence or eight effective draws.

Scientific mechanism: Metropolis et al. (1953), doi:10.1063/1.1699114.
Related rejuvenation motivation: Gilks and Berzuini (2001),
https://academic.oup.com/jrsssb/article-abstract/63/1/127/7083331 .
This is independent-chain MCMC, not an implementation of their SMC algorithm.
"""
import random

from calibrated_beliefs import BeliefModel

VERSION='independent-rank-swap-metropolis-v1'


def rejuvenate(world,slots,histories,likelihoods,rng,steps):
    """Modify one count-consistent world with a lazy symmetric swap kernel."""
    size=len(slots);accepted=0
    if size<2:return 0
    for _ in range(steps):
        i,j=rng.randrange(size),rng.randrange(size)
        if i==j:continue
        first,second=slots[i],slots[j]
        a,b=world[first]&15,world[second]&15
        if a==b or not histories[first][-1]&(1<<b) or not histories[second][-1]&(1<<a):continue
        ratio=likelihoods[first][b]*likelihoods[second][a]/(likelihoods[first][a]*likelihoods[second][b])
        if ratio>=1 or rng.random()<ratio:
            world[first]=(world[first]&240)|b;world[second]=(world[second]&240)|a
            accepted+=1
    return accepted


class SwapBeliefs:
    def __init__(self,belief_model,sweeps=4):
        if not isinstance(sweeps,int) or isinstance(sweeps,bool) or sweeps<0:raise ValueError('nonnegative integer sweeps required')
        self.belief_model=belief_model;self.sweeps=sweeps;self.last_report={}

    @classmethod
    def load(cls,path,sweeps=4):return cls(BeliefModel.load(path),sweeps)

    def sample_worlds(self,cells,lost,histories,rng,army,samples):
        if not isinstance(samples,int) or isinstance(samples,bool) or samples<1:raise ValueError('positive integer samples required')
        slots,remaining,likelihoods=self.belief_model.prepare(cells,lost,histories,army)
        # Actual observer masks are all-rank or moved. For arbitrary narrower
        # masks, legal pair swaps can form disconnected components; do not
        # silently imply an irreducible chain for such future extensions.
        if any(histories[sq][-1] not in (1023,4095) for sq in slots):
            raise ValueError('swap sampler supports ordinary all-rank/moved masks only')
        steps=self.sweeps*len(slots);draws=[];accepted=0
        for _ in range(samples):
            chain=random.Random(rng.getrandbits(64))
            world,_=self.belief_model.draw(cells,histories,chain,slots,remaining,likelihoods)
            accepted+=rejuvenate(world,slots,histories,likelihoods,chain,steps)
            draws.append((world,1.))
        self.last_report=dict(version=VERSION,chains=samples,sweeps=self.sweeps,
                              attempted_swaps=steps*samples,accepted_rank_changes=accepted,
                              finite_burn_in_approximation=True)
        return draws
