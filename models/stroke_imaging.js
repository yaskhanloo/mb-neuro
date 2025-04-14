// epic_imaging.js
export default (sequelize, DataTypes) => {
  const EPICImaging = sequelize.define('epic_imaging', {
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
    firstimage_type: {
      type: DataTypes.STRING,
      allowNull: true,
    },
    firstimage_result: {
      type: DataTypes.STRING,
      allowNull: true,
    },
    firstimage_time: {
      type: DataTypes.DATE,
      allowNull: true,
    },
    firstangio_type: {
      type: DataTypes.STRING,
      allowNull: true,
    },
    iat_mech: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    follow_mra: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    follow_cta: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    follow_ultrasound: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    follow_dsa: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    follow_tte: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    follow_tee: {
      type: DataTypes.BOOLEAN,
      allowNull: true,
    },
    follow_holter: {
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
  
  EPICImaging.associate = function (models) {
    // associations can be defined here
    EPICImaging.belongsTo(models.PatientClinic, {
      as: 'patient',
      foreignKey: 'idPatient',
    });
  };
  
  return EPICImaging;
};