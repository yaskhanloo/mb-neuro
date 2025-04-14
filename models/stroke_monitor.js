// epic_monitor.js
export default (sequelize, DataTypes) => {
  const EPICMonitor = sequelize.define('epic_monitor', {
    id: {
      type: DataTypes.BIGINT,
      autoIncrement: true,
      primaryKey: true,
    },
    idCase: {
      type: DataTypes.STRING,
    },
    idPatient: {
      type: DataTypes.BIGINT,
      allowNull: false,
    },
    FID: {
      type: DataTypes.INTEGER,
      allowNull: true,
    },
    SSR: {
      type: DataTypes.INTEGER,
      allowNull: true,
    },
    INCLUSION_STROKE_DOCUMENTATION: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    INCLUSION_STROKE_FLAG: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    DOOR_TO_NEEDLE: {
      type: DataTypes.INTEGER,
      allowNull: true,
    },
    GROIN_PUNCTURE: {
      type: DataTypes.DATE,
      allowNull: true,
    },
    DOOR_TO_GROIN: {
      type: DataTypes.INTEGER,
      allowNull: true,
    },
    DOOR_TO_RECAN: {
      type: DataTypes.INTEGER,
      allowNull: true,
    },
    ELIG_IA: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    ELIG_IV: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    createdAt: {
      type: DataTypes.DATE,
      allowNull: true,
    },
    updatedAt: {
      type: DataTypes.DATE,
      allowNull: true,
    },
  });
  
  EPICMonitor.associate = function (models) {
    // associations can be defined here
    EPICMonitor.belongsTo(models.PatientClinic, {
      as: 'patient',
      foreignKey: 'idPatient',
    });
  };
  
  return EPICMonitor;
};