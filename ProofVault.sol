// SPDX-License-Identifier: MIT
pragma solidity ^0.8.18;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

interface IVerifier {
    /// @notice Returns true if the given proof calldata is valid.
    function verify(bytes calldata proofAndInputs) external view returns (bool);
}

contract ProofVault is ReentrancyGuard {
    IVerifier public immutable verifier;

    event Claimed(address indexed user, uint256 amount);
    event Deposited(address indexed sender, uint256 amount);

    constructor(address _verifier) {
        verifier = IVerifier(_verifier);
    }

    /// @notice Accept ETH deposits into the vault.
    receive() external payable {
        emit Deposited(msg.sender, msg.value);
    }

    fallback() external payable {
        emit Deposited(msg.sender, msg.value);
    }

    /// @notice Verify proof; if valid, transfer all ETH to caller.
    /// @param proofAndInputs ABI-encoded bytes from `ezkl encode-evm-calldata`.
    function claimWithProof(bytes calldata proofAndInputs) external nonReentrant {
        bool valid = verifier.verify(proofAndInputs);
        require(valid, "Invalid proof");

        uint256 balance = address(this).balance;
        require(balance > 0, "No funds to claim");

        // send all ETH to caller
        (bool sent, ) = msg.sender.call{value: balance}("");
        require(sent, "ETH transfer failed");

        emit Claimed(msg.sender, balance);
    }
}
