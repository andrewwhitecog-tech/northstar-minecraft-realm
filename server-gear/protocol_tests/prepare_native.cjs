// Select the package's own platform/architecture prebuild when the kernel major changed.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const helper=require('raknet-native/helpers/buildPath');const expected=helper.getPath();
if(!fs.existsSync(expected)){const bundled=helper.getFallbackPath();if(!bundled)throw Error('No bundled native RakNet for this platform');fs.mkdirSync(path.dirname(expected),{recursive:true});fs.copyFileSync(bundled,expected);console.log('Bundled native RakNet kernel-path adaptation',JSON.stringify({source:path.relative(__dirname,bundled),target:path.relative(__dirname,expected),sha256:crypto.createHash('sha256').update(fs.readFileSync(expected)).digest('hex')}));}
const native=require('raknet-native');if(typeof native.RakClient!=='function'||typeof native.Client!=='function')throw Error('Native RakNet load failed');console.log('Actual native RakNet exports loaded; Bedrock transport protocol11');
