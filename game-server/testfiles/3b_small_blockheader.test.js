const BrokenRelay = artifacts.require("./BrokenRelay.sol")
const Utils = artifacts.require("./Utils.sol")

const constants = require("./constants")
const helpers = require('./helpers');
const truffleAssert = require('truffle-assertions');

const testdata = require('./testdata/blocks.json')


var dblSha256Flip = helpers.dblSha256Flip
var flipBytes = helpers.flipBytes

contract('Attack Test Cases', async(accounts) => {

    const storeGenesis = async function(){
        genesis = testdata[0]
        await relay.setInitialParent(
            genesis["header"],
            genesis["height"],
            );
    }


    beforeEach('(re)deploy contracts', async function (){ 
        relay = await BrokenRelay.new();
        utils = await Utils.deployed();
    });



    it("TESTCASE 3b: too small block header - should fail", async () => {   
        storeGenesis();  
        block1 = testdata[1]    
        await truffleAssert.reverts(
            relay.submitBlockHeader(
                block1["header"].substring(0,28)
                ),
                constants.ERROR_CODES.ERR_INVALID_HEADER
            );
    });


});