#!/usr/bin/env python3

import unittest
from hashlib import sha256

from btclib.ellipticcurves import jac_from_affine, secp256k1, \
                                  mod_inv
from btclib.ecdsa import rfc6979, int_from_hash, \
                         _ecdsa_sign_raw, ecdsa_sign, \
                         _ecdsa_verify_raw, ecdsa_verify, \
                         _ecdsa_pubkey_recovery_raw, ecdsa_pubkey_recovery

from tests.test_ellipticcurves import lowcard

class TestEcdsa(unittest.TestCase):
    def test_ecdsa(self):
        q = 0x1
        Q = secp256k1.pointMultiply(q, secp256k1.G)
        msg = 'Satoshi Nakamoto'

        dsasig = ecdsa_sign(msg, q)
        self.assertTrue(ecdsa_verify(msg, dsasig, Q))
        # malleability
        malleated_sig = (dsasig[0], secp256k1.n - dsasig[1])
        self.assertTrue(ecdsa_verify(msg, malleated_sig, Q))

        keys = ecdsa_pubkey_recovery(msg, dsasig)
        self.assertIn(Q, keys)

        # source: https://bitcointalk.org/index.php?topic=285142.40
        exp_sig = (0x934b1ea10a4b3c1757e2b0c017d0b6143ce3c9a7e6a4a49860d7a6ab210ee3d8,
                   0x2442ce9d2b916064108014783e923ec36b49743e2ffa1c4496f01a512aafd9e5)
        r, s = dsasig
        self.assertEqual(r, exp_sig[0])
        sigs = (exp_sig[1], secp256k1.n - exp_sig[1])
        self.assertIn(s, sigs)

    def test_low_cardinality(self):
        """test all msg/key pairs of low cardinality elliptic curves"""

        # ec.n has to be prime to sign
        prime = [
              3,   5,   7,  11,  13,  17,  19,  23,  29,  31,
             37,  41,  43,  47,  53,  59,  61,  67,  71,  73#,
            # 79,  83,  89,  97, 101, 103, 107, 109, 113, 127,
            #131, 137, 139, 149, 151, 157, 163, 167, 173, 179,
            #181, 191, 193, 197, 199, 211, 223, 227, 229, 233,
            #239, 241, 251, 257, 263, 269, 271, 277, 281, 283
            ]

        # all possible hashed messages
        hlen = 32
        H = [i.to_bytes(hlen, 'big') for i in range(0, max(prime))]

        for ec in lowcard:
            if ec.n in prime:
                for q in range(1, ec.n): # all possible private keys
                    G = jac_from_affine(ec.G) # G in jacobian coordinates
                    Q = ec.pointMultiplyJacobian(q, G) # public key
                    for m in range(0, ec.n): # all possible hashed messages

                        k = rfc6979(q, H[m], sha256) # ephemeral key
                        K = ec.pointMultiplyJacobian(k, G)
                        if K == None:
                            self.assertRaises(ValueError, _ecdsa_sign_raw, H[m], q, k, ec)
                            continue

                        r = K[0] % ec.n
                        if r == 0:
                            self.assertRaises(ValueError, _ecdsa_sign_raw, H[m], q, k, ec)
                            continue

                        e = int_from_hash(H[m], ec.n)
                        s = mod_inv(k, ec.n) * (e + q * r) % ec.n
                        if s == 0:
                            print("it does not enter here")
                            self.assertRaises(ValueError, _ecdsa_sign_raw, H[m], q, k, ec)
                            continue

                        # valid signature
                        sig = _ecdsa_sign_raw(H[m], q, k, ec)
                        self.assertEqual((r, s), sig)
                        # valid signature must validate
                        self.assertTrue(_ecdsa_verify_raw(H[m], sig, Q, ec))
                        # malleated signature must validate
                        malleated_sig = (sig[0], ec.n - sig[1])
                        self.assertTrue(_ecdsa_verify_raw(H[m], malleated_sig, Q, ec))
                        # key recovery
                        keys = _ecdsa_pubkey_recovery_raw(H[m], sig, ec)
                        self.assertIn(Q, keys)

if __name__ == "__main__":
    # execute only if run as a script
    unittest.main()
