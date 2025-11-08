# missed-rewards-bug-polkadot

Repository to share my work to help detecting wallets affected by the staking rewards bug in Polkadot runtime from era 1981

## General idea

`REWARD_DIVIDER` was calculated as: `wrong_fixed_total_issuance / correct_fixed_total_issuance`  
`5216342402773185773 / 15011657390566252333 = 0.3474861080996481`

Overall the idea is:

```
original_reward = received_reward / (wrong_fixed_total_issuance / correct_fixed_total_issuance)
original_reward = received_reward / 0.3474861080996481
```

Example:

```
original_reward = 88116166200 / (5216342402773185773 / 15011657390566252333)
= 88116166200  / 0.3474861080996481
= 253581838657.9387
= 25.358 DOT
```

Issuance levels are extracted from: https://github.com/polkadot-fellows/runtimes/pull/998/files#diff-02eb31199deb234b1df06a7173bf2f4694dbf9e34139e20063d89a5efd86246aL304