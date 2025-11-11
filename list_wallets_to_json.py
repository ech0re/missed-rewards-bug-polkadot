#!/usr/bin/env python3

import json
from substrateinterface import SubstrateInterface

ERAS = [1981, 1982, 1983, 1984, 1985, 1986]
RPC_ASSETHUB = "wss://dot-rpc.stakeworld.io/assethub"
DOT_DECIMALS = 10
PLANCK_PER_DOT = 10 ** DOT_DECIMALS
REWARD_DIVIDER = 0.3474861080996481

"""
REWARD_DIVIDER was calculated as: wrong_fixed_total_issuance / correct_fixed_total_issuance
5216342402773185773 / 15011657390566252333 = 0.3474861080996481

Overall the idea is:
original_reward = received_reward / (wrong_fixed_total_issuance / correct_fixed_total_issuance)
original_reward = received_reward / 0.3474861080996481

Example:
original_reward = 88116166200 / (5216342402773185773 / 15011657390566252333)
= 88116166200  / 0.3474861080996481
= 253581838657.9387
= 25.358 DOT
"""

def planck_to_dot(planck):
    """Convert plancks to DOT"""
    if planck is None or planck == 0:
        return "0.0000000000"
    return f"{planck / PLANCK_PER_DOT:.10f}"

substrate = SubstrateInterface(url=RPC_ASSETHUB)

output = {}

for era in ERAS:
    print(f"=== ERA {era} ===")
    
    # Get the total reward for the era
    era_reward_opt = substrate.query("Staking", "ErasValidatorReward", [era])
    if not era_reward_opt.value:
        print(f"No reward for era {era}\n")
        continue
    
    era_reward = int(era_reward_opt.value)
    print(f"Total reward for era: {planck_to_dot(era_reward)} DOT")
    
    # Get the points for the era
    points = substrate.query("Staking", "ErasRewardPoints", [era])
    if not points.value:
        print(f"No data for era {era}\n")
        continue
    
    total_points = int(points.value.get('total', 0))
    individual_points = points.value.get('individual', [])
    
    # Get the list of validators and their points
    points_map = {}
    validators = []
    if isinstance(individual_points, list):
        for item in individual_points:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                validator_addr = item[0]
                validator_points = int(item[1])
                validators.append(validator_addr)
                points_map[validator_addr] = validator_points
    
    print(f"Number of validators: {len(validators)}")
    
    validator_rewards = {}
    nominator_rewards = {}
    
    # Calculate the rewards for each validator
    for i, validator in enumerate(validators, 1):
        if i % 50 == 0:
            print(f"  Processing validator {i}/{len(validators)}...")
        
        v_points = points_map.get(validator, 0)
        if v_points == 0 or total_points == 0:
            validator_rewards[validator] = 0
            continue
        
        # Raw reward for the validator
        validator_reward = (era_reward * v_points) // total_points
        
        # Commission rate
        prefs = substrate.query("Staking", "ErasValidatorPrefs", [era, validator])
        commission_perbill = 0
        if prefs.value:
            commission_perbill = int(prefs.value.get('commission', 0))
        
        COMM_DEN = 1_000_000_000
        commission_amt = (validator_reward * commission_perbill) // COMM_DEN
        pool_remainder = validator_reward - commission_amt
        
        overview = substrate.query("Staking", "ErasStakersOverview", [era, validator])
        if not overview.value:
            validator_rewards[validator] = commission_amt
            continue
        
        total_stake = int(overview.value.get('total', 0))
        own_stake = int(overview.value.get('own', 0))
        page_count = int(overview.value.get('page_count', 0))
        
        # Validator share = commission + their share of the pool
        if total_stake > 0 and pool_remainder > 0:
            v_share = (pool_remainder * own_stake) // total_stake
            validator_rewards[validator] = commission_amt + v_share
        else:
            validator_rewards[validator] = commission_amt
        
        # Get all nominators and calculate their shares
        if total_stake > 0 and pool_remainder > 0:
            for page in range(page_count):
                try:
                    paged = substrate.query("Staking", "ErasStakersPaged", [era, validator, page])
                    if not paged.value:
                        break
                    
                    for nominator in paged.value.get('others', []):
                        nom_addr = nominator.get('who')
                        nom_stake = int(nominator.get('value', 0))
                        
                        if nom_stake > 0:
                            n_share = (pool_remainder * nom_stake) // total_stake
                            
                            if nom_addr not in nominator_rewards:
                                nominator_rewards[nom_addr] = 0
                            nominator_rewards[nom_addr] += n_share
                except:
                    break
    
    print(f"Number of unique nominators: {len(nominator_rewards)}")
    
    # Nominators are currently not linked to the validators, I assume this isn't needed
    validators_data = []
    for validator in validators:
        reward_planck = validator_rewards.get(validator, 0)
        reward_dot = planck_to_dot(reward_planck)
        expected_dot = f"{float(reward_dot) / REWARD_DIVIDER:.10f}"
        
        validators_data.append({
            'address': validator,
            'reward': reward_dot,
            'expected': expected_dot
        })
    
    nominators_data = []
    for nominator, reward_planck in sorted(nominator_rewards.items()):
        reward_dot = planck_to_dot(reward_planck)
        expected_dot = f"{float(reward_dot) / REWARD_DIVIDER:.10f}"
        
        nominators_data.append({
            'address': nominator,
            'reward': reward_dot,
            'expected': expected_dot
        })
    
    output[era] = {
        'validator_count': len(validators_data),
        'validators': validators_data,
        'nominator_count': len(nominators_data),
        'nominators': nominators_data
    }

# Write the JSON file
filename = "wallets_list.json"
with open(filename, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"\nFile written: {filename}")

substrate.close()

