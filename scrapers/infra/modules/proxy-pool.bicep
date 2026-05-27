param location string
param adminUsername string
@secure()
param adminPassword string
param tags object

var count = 3

resource vnet 'Microsoft.Network/virtualNetworks@2023-11-01' = {
  name: 'cdp-proxy-vnet'
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.42.0.0/16'
      ]
    }
    subnets: [
      {
        name: 'proxy'
        properties: {
          addressPrefix: '10.42.1.0/24'
        }
      }
    ]
  }
}

resource nsg 'Microsoft.Network/networkSecurityGroups@2023-11-01' = {
  name: 'cdp-proxy-nsg'
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'allow-authenticated-proxy-port'
        properties: {
          priority: 1000
          protocol: 'Tcp'
          access: 'Allow'
          direction: 'Inbound'
          sourceAddressPrefix: '*'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '3128'
        }
      }
    ]
  }
}

resource publicIps 'Microsoft.Network/publicIPAddresses@2023-11-01' = [for i in range(0, count): {
  name: 'cdp-proxy-${i + 1}-pip'
  location: location
  tags: tags
  sku: {
    name: 'Standard'
  }
  properties: {
    publicIPAllocationMethod: 'Static'
  }
}]

resource nics 'Microsoft.Network/networkInterfaces@2023-11-01' = [for i in range(0, count): {
  name: 'cdp-proxy-${i + 1}-nic'
  location: location
  tags: tags
  properties: {
    networkSecurityGroup: {
      id: nsg.id
    }
    ipConfigurations: [
      {
        name: 'ipconfig1'
        properties: {
          subnet: {
            id: vnet.properties.subnets[0].id
          }
          privateIPAllocationMethod: 'Dynamic'
          publicIPAddress: {
            id: publicIps[i].id
          }
        }
      }
    ]
  }
}]

resource vms 'Microsoft.Compute/virtualMachines@2023-09-01' = [for i in range(0, count): {
  name: 'cdp-proxy-${i + 1}'
  location: location
  tags: tags
  properties: {
    hardwareProfile: {
      vmSize: 'Standard_B1s'
    }
    osProfile: {
      computerName: 'cdp-proxy-${i + 1}'
      adminUsername: adminUsername
      adminPassword: adminPassword
      linuxConfiguration: {
        disablePasswordAuthentication: false
      }
      customData: base64('''#cloud-config
package_update: true
packages:
  - squid
runcmd:
  - systemctl enable squid
  - systemctl restart squid
''')
    }
    storageProfile: {
      imageReference: {
        publisher: 'Canonical'
        offer: '0001-com-ubuntu-server-jammy'
        sku: '22_04-lts-gen2'
        version: 'latest'
      }
      osDisk: {
        createOption: 'FromImage'
        managedDisk: {
          storageAccountType: 'Standard_LRS'
        }
      }
    }
    networkProfile: {
      networkInterfaces: [
        {
          id: nics[i].id
        }
      ]
    }
  }
}]

output publicIpAddresses array = [for i in range(0, count): publicIps[i].properties.ipAddress]
