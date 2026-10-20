import numpy as np
from peer_ranking import pair_concordance


def test_discordant_peer_pairs_and_ties():
    values,mask=pair_concordance([.8,.3,.4,.2,.8],[.2,.8,.4,.9,.1],[1,0,1,1,np.nan],[0,1,0,1,0])
    np.testing.assert_array_equal(mask,[True,True,True,False,False])
    np.testing.assert_array_equal(values,[1.,1.,.5])
