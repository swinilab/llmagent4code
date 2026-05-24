module.exports = (sequelize) => {
  return sequelize.define('Payment', {
    id: { type: DataTypes.UUID, primaryKey: true, defaultValue: DataTypes.UUIDV4 },
    orderId: { type: DataTypes.UUID, allowNull: false },
    amount: { type: DataTypes.DECIMAL(10, 2), allowNull: false },
    paymentMethod: { type: DataTypes.STRING, allowNull: false },
    status: { type: DataTypes.STRING, defaultValue: 'pending' }, // e.g., pending, completed
    transactionDate: { type: DataTypes.DATE, defaultValue: DataTypes.NOW }
  });
};