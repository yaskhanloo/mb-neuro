// epic_medication.js
export default (sequelize, DataTypes) => {
  const EPICMedication = sequelize.define('epic_medication', {
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
    aspirin_pre: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    clopidogrel_pre: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    prasugrel_pre: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    ticagrelor_pre: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    dipyridamole_pre: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    vka_pre: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    vka_inr: {
      type: DataTypes.FLOAT,
      allowNull: true,
    },
    rivaroxaban_pre: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    dabigatran_pre: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    apixaban_pre: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    edoxaban_pre: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    parenteralanticg_pre: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    antihypertensive_pre: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    antilipid_pre: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    hormone_pre: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    treat_antiplatelet: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    treat_anticoagulant: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    treat_ivt: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    iat_rtpa: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    iat_uk: {
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
  
  EPICMedication.associate = function (models) {
    // associations can be defined here
    EPICMedication.belongsTo(models.PatientClinic, {
      as: 'patient',
      foreignKey: 'idPatient',
    });
  };
  
  return EPICMedication;
};