const { DataTypes } = require('sequelize');

module.exports = (sequelize) => {
  return sequelize.define('Customer', {
    id: { type: DataTypes.UUID, primaryKey: true, defaultValue: DataTypes.UUIDV4 },
    name: { type: DataTypes.STRING, allowNull: false },
    address: { type: DataTypes.TEXT, allowNull: false },
    phone: { type: DataTypes.STRING, allowNull: false },
    bankingDetails: { type: DataTypes.JSONB, allowNull: false },
    orderHistory: { type: DataTypes.JSONB, allowNull: true }, // Store references to orders
    userRole: { type: DataTypes.ENUM('customer', 'order_staff', 'accountant'), defaultValue: 'customer' }
  });
};