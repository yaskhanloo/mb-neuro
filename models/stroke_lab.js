// epic_lab.js
export default (sequelize, DataTypes) => {
  const EPICLab = sequelize.define('epic_lab', {
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
    inr: {
      type: DataTypes.FLOAT,
      allowNull: true,
    },
    glucose: {
      type: DataTypes.FLOAT,
      allowNull: true,
    },
    creatinine: {
      type: DataTypes.FLOAT,
      allowNull: true,
    },
    cholesterol_total: {
      type: DataTypes.FLOAT,
      allowNull: true,
    },
    cholesterol_ldl: {
      type: DataTypes.FLOAT,
      allowNull: true,
    },
    admis_platelets: {
      type: DataTypes.INTEGER,
      allowNull: true,
    },
    admis_haem: {
      type: DataTypes.FLOAT,
      allowNull: true,
    },
    admis_lecuco: {
      type: DataTypes.FLOAT,
      allowNull: true,
    },
    admis_crp: {
      type: DataTypes.FLOAT,
      allowNull: true,
    },
    level_doac: {
      type: DataTypes.FLOAT,
      allowNull: true,
    },
    perfusion_type: {
      type: DataTypes.STRING,
      allowNull: true,
    },
    perfusion_result: {
      type: DataTypes.STRING,
      allowNull: true,
    },
    onset_treat_time: {
      type: DataTypes.DATE,
      allowNull: true,
    },
    door_treat_time: {
      type: DataTypes.DATE,
      allowNull: true,
    },
    treat_iat: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    iat_start: {
      type: DataTypes.DATE,
      allowNull: true,
    },
    onset_iat_time: {
      type: DataTypes.DATE,
      allowNull: true,
    },
    door_iat_time: {
      type: DataTypes.DATE,
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
  
  EPICLab.associate = function (models) {
    // associations can be defined here
    EPICLab.belongsTo(models.PatientClinic, {
      as: 'patient',
      foreignKey: 'idPatient',
    });
  };
  
  return EPICLab;
};