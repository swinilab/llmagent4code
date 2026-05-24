module.exports = (sequelize) => {
  return sequelize.define('Order', {
    id: { type: DataTypes.UUID, primaryKey: true, defaultValue: DataTypes.UUIDV4 },
    customerId: { type: DataTypes.UUID, allowNull: false },
    orderDetails: { type: DataTypes.JSONB, allowNull: false },
    status: { type: DataTypes.STRING, defaultValue: 'pending' }, // e.g., pending, accepted, completed
    createdDate: { type: DataTypes.DATE, defaultValue: DataTypes.NOW },
    updatedDate: { type: DataTypes.DATE, defaultValue: DataTypes.NOW }
  });
};