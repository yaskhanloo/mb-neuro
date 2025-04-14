export default (sequelize, DataTypes) => {
  const EPICEncounter = sequelize.define('epic_encounter', {
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
    name_last: {
      type: DataTypes.STRING,
      allowNull: true,
    },
    name_first: {
      type: DataTypes.STRING,
      allowNull: true,
    },
    birth_date: {
      type: DataTypes.DATE,
      allowNull: true,
    },
    sex: {
      type: DataTypes.STRING,
      allowNull: true,
    },
    non_swiss: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    zip: {
      type: DataTypes.STRING,
      allowNull: true,
    },
    arrival_date: {
      type: DataTypes.DATE,
      allowNull: true,
    },
    arrival_time: {
      type: DataTypes.TIME,
      allowNull: true,
    },
    height: {
      type: DataTypes.INTEGER,
      allowNull: true,
    },
    weight: {
      type: DataTypes.INTEGER,
      allowNull: true,
    },
    bmi: {
      type: DataTypes.FLOAT,
      allowNull: true,
    },
    transport: {
      type: DataTypes.STRING,
      allowNull: true,
    },
    living_pre: {
      type: DataTypes.STRING,
      allowNull: true,
    },
    discharge_date: {
      type: DataTypes.DATE,
      allowNull: true,
    },
    discharge_time: {
      type: DataTypes.TIME,
      allowNull: true,
    },
    discharge_destinat: {
      type: DataTypes.STRING,
      allowNull: true,
    },
    age: {
      type: DataTypes.INTEGER,
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
  
  EPICEncounter.associate = function (models) {
    // associations can be defined here
    EPICEncounter.belongsTo(models.PatientClinic, {
      as: 'patient',
      foreignKey: 'idPatient',
    });
  };
  
  return EPICEncounter;
};