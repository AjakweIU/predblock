/**
 * PureChain Bridge for PredBlock
 * Node.js service that provides PureChain blockchain access to Python
 */

const express = require('express');
const bodyParser = require('body-parser');
const PureChain = require('purechainlib');

const app = express();
app.use(bodyParser.json());

// Initialize PureChain
let purechain = null;
let connectedAddress = null;

// Configuration
const PORT = process.env.PURECHAIN_BRIDGE_PORT || 3000;
const NETWORK = process.env.PURECHAIN_NETWORK || 'testnet';

/**
 * Initialize PureChain connection
 */
app.post('/api/init', async (req, res) => {
    try {
        const { network, privateKey } = req.body;
        
        purechain = new PureChain(network || NETWORK);
        
        if (privateKey) {
            purechain.connect(privateKey);
            connectedAddress = (await purechain.getSigner()).address;
        }
        
        res.json({
            success: true,
            network: await purechain.network(),
            address: connectedAddress
        });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

/**
 * Create new account
 */
app.post('/api/account/create', async (req, res) => {
    try {
        if (!purechain) {
            purechain = new PureChain(NETWORK);
        }
        
        const account = purechain.account();
        
        res.json({
            success: true,
            account: {
                address: account.address,
                privateKey: account.privateKey,
                mnemonic: account.mnemonic
            }
        });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

/**
 * Connect account
 */
app.post('/api/account/connect', async (req, res) => {
    try {
        const { privateKey } = req.body;
        
        if (!purechain) {
            purechain = new PureChain(NETWORK);
        }
        
        purechain.connect(privateKey);
        connectedAddress = (await purechain.getSigner()).address;
        
        res.json({
            success: true,
            address: connectedAddress
        });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

/**
 * Get balance
 */
app.get('/api/balance/:address?', async (req, res) => {
    try {
        if (!purechain) {
            throw new Error('PureChain not initialized');
        }
        
        const address = req.params.address || connectedAddress;
        const balance = await purechain.balance(address);
        
        res.json({
            success: true,
            address: address,
            balance: balance
        });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

/**
 * Deploy contract
 */
app.post('/api/contract/deploy', async (req, res) => {
    try {
        if (!purechain) {
            throw new Error('PureChain not initialized');
        }
        
        const { source, constructorArgs } = req.body;
        
        // Compile contract
        const factory = await purechain.contract(source);
        
        // Deploy contract
        const contract = await factory.deploy(...(constructorArgs || []));
        const address = await contract.getAddress();
        
        res.json({
            success: true,
            contractAddress: address,
            abi: factory.getABI()
        });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

/**
 * Call contract method (read-only)
 */
app.post('/api/contract/call', async (req, res) => {
    try {
        if (!purechain) {
            throw new Error('PureChain not initialized');
        }
        
        const { contractAddress, abi, method, args } = req.body;
        
        // Get contract instance
        const contract = new (await purechain.getProvider()).Contract(
            contractAddress,
            abi,
            await purechain.getSigner()
        );
        
        // Call method
        const result = await purechain.call(contract, method, ...(args || []));
        
        res.json({
            success: true,
            result: result
        });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

/**
 * Execute contract method (state-changing)
 */
app.post('/api/contract/execute', async (req, res) => {
    try {
        if (!purechain) {
            throw new Error('PureChain not initialized');
        }
        
        const { contractAddress, abi, method, args } = req.body;
        
        // Get contract instance
        const contract = new (await purechain.getProvider()).Contract(
            contractAddress,
            abi,
            await purechain.getSigner()
        );
        
        // Execute method
        const receipt = await purechain.execute(contract, method, ...(args || []));
        
        res.json({
            success: true,
            transactionHash: receipt.hash,
            receipt: receipt
        });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

/**
 * Send transaction
 */
app.post('/api/transaction/send', async (req, res) => {
    try {
        if (!purechain) {
            throw new Error('PureChain not initialized');
        }
        
        const { to, value } = req.body;
        
        const receipt = await purechain.send(to, value);
        
        res.json({
            success: true,
            transactionHash: receipt.hash,
            receipt: receipt
        });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

/**
 * Get transaction
 */
app.get('/api/transaction/:hash', async (req, res) => {
    try {
        if (!purechain) {
            throw new Error('PureChain not initialized');
        }
        
        const tx = await purechain.transaction(req.params.hash);
        
        res.json({
            success: true,
            transaction: tx
        });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

/**
 * Get block
 */
app.get('/api/block/:number?', async (req, res) => {
    try {
        if (!purechain) {
            throw new Error('PureChain not initialized');
        }
        
        const blockNumber = req.params.number || 'latest';
        const block = await purechain.block(blockNumber);
        
        res.json({
            success: true,
            block: block
        });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

/**
 * Get network status
 */
app.get('/api/status', async (req, res) => {
    try {
        if (!purechain) {
            purechain = new PureChain(NETWORK);
        }
        
        const status = await purechain.status();
        
        res.json({
            success: true,
            status: status
        });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

/**
 * Health check
 */
app.get('/health', (req, res) => {
    res.json({
        success: true,
        status: 'running',
        network: NETWORK,
        connected: connectedAddress !== null,
        address: connectedAddress
    });
});

// Start server
app.listen(PORT, () => {
    console.log(`PureChain Bridge running on port ${PORT}`);
    console.log(`Network: ${NETWORK}`);
    console.log(`Endpoint: http://localhost:${PORT}`);
});
